import { expect, test, type Page } from '@playwright/test';

// Base de démonstration neuve (voir playwright.config.ts). Lecture seule.

async function contraste(page: Page, selecteur: string) {
	return page.locator(selecteur).first().evaluate((el) => {
		const ctx = document.createElement('canvas').getContext('2d', { willReadFrequently: true })!;
		const rgba = (c: string) => {
			ctx.clearRect(0, 0, 1, 1);
			ctx.fillStyle = c;
			ctx.fillRect(0, 0, 1, 1);
			const [r, g, b, a] = ctx.getImageData(0, 0, 1, 1).data;
			return { r, g, b, a: a / 255 };
		};
		const sur = (h: { r: number; g: number; b: number; a: number }, d: { r: number; g: number; b: number }) => ({
			r: h.r * h.a + d.r * (1 - h.a),
			g: h.g * h.a + d.g * (1 - h.a),
			b: h.b * h.a + d.b * (1 - h.a)
		});
		const couches: ReturnType<typeof rgba>[] = [];
		for (let n: Element | null = el; n; n = n.parentElement) couches.unshift(rgba(getComputedStyle(n).backgroundColor));
		let fond = { r: 255, g: 255, b: 255 };
		for (const c of couches) fond = sur(c, fond);
		const texte = sur(rgba(getComputedStyle(el).color), fond);
		const lum = ({ r, g, b }: { r: number; g: number; b: number }) => {
			const [R, G, B] = [r, g, b].map((v) => {
				const c = v / 255;
				return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
			});
			return 0.2126 * R + 0.7152 * G + 0.0722 * B;
		};
		const [clair, sombre] = [lum(texte), lum(fond)].sort((a, b) => b - a);
		return (clair + 0.05) / (sombre + 0.05);
	});
}

for (const theme of ['light', 'dark'] as const) {
	test(`accueil : contraste d'au moins 4,5:1 en thème ${theme}`, async ({ page }) => {
		await page.emulateMedia({ colorScheme: theme });
		await page.goto('/');
		const styles: Record<string, string> = {
			titre: 'h1',
			'texte discret': 'main p.discret',
			'lien de navigation': 'header nav a',
			'chiffre en carte': '.cartes .nombre',
			'texte en carte': '.cartes li'
		};
		for (const [quoi, selecteur] of Object.entries(styles))
			expect(await contraste(page, selecteur), `${quoi} (${theme})`).toBeGreaterThanOrEqual(4.5);
		await page.screenshot({ path: `test-results/accueil-${theme}.png`, fullPage: true });
	});
}

test('accueil : la base de démonstration est connectée et la page est en français', async ({ page }) => {
	await page.goto('/');
	await expect(page.getByRole('heading', { level: 1, name: 'Tableau de bord du Dénicheur' })).toBeVisible();
	await expect(page.getByText('candidatures suivies')).toBeVisible();
	expect(await page.locator('html').getAttribute('lang')).toBe('fr');
	await expect(page).toHaveTitle(/Accueil/);
});

test('clavier : lien d’évitement, puis focus visible sur chaque contrôle', async ({ page }) => {
	await page.goto('/');
	await page.keyboard.press('Tab');
	const evitement = page.getByRole('link', { name: 'Aller au contenu' });
	await expect(evitement).toBeFocused();
	await expect(evitement).toBeInViewport();
	await page.keyboard.press('Enter');
	await expect(page).toHaveURL(/#contenu$/);

	await page.goto('/introuvable'); // page d'erreur : le focus repart du haut du document
	for (let i = 0; i < 2; i++) { // lien d’évitement et « Accueil » : les seuls contrôles de cette page
		await page.keyboard.press('Tab');
		const focus = await page.evaluate(() => {
			const el = document.activeElement as HTMLElement;
			const s = getComputedStyle(el);
			return {
				nom: (el.textContent ?? '').trim().slice(0, 30),
				visible: (s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) > 0) || s.boxShadow !== 'none'
			};
		});
		expect(focus.visible, `focus visible sur « ${focus.nom} »`).toBe(true);
	}
});

test('une page inconnue affiche une erreur lisible dans la mise en page', async ({ page }) => {
	const reponse = await page.goto('/introuvable');
	expect(reponse?.status()).toBe(404);
	await expect(page.getByRole('alert')).toBeVisible();
	await expect(page.getByRole('navigation', { name: 'Pages du tableau de bord' })).toBeVisible();
});

test('l’hôte étranger est refusé', async ({ request }) => {
	const reponse = await request.get('/', { headers: { host: 'exemple.fr' } });
	expect(reponse.status()).toBe(403);
});
