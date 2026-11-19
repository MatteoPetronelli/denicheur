import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';

// Accessibilité mesurée dans un vrai navigateur, en lecture seule (base de démonstration, voir graine.ts).

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

const STYLES: Record<string, Record<string, string>> = {
	'/': {
		titre: 'h1',
		'titre de colonne': '.tableau h2',
		'titre de carte': '.carte h3 a',
		'texte de carte': '.carte p',
		badge: '.puces .badge',
		menu: '.menu summary',
		'lien externe': '.carte a[target]',
		bouton: 'button.btn-secondaire',
		'navigation': 'header nav a'
	},
	'/entreprises': {
		'en-tête de tableau': 'thead th',
		'nom': 'tbody th a',
		'cellule': 'tbody td',
		'bouton secondaire': 'button.btn-secondaire',
		'pagination': '.pagination a',
		'page courante': '.pagination .courante',
		'statut': 'tbody .badge',
		'sous-ligne': 'tbody .sous.discret'
	},
	'/offres': { 'en-tête de tableau': 'thead th', 'étiquette seuil': '.badge.avertissement', cellule: 'tbody td' },
	'/stats': { titre: 'h1', 'sous-titre': 'h2', 'étape': '.entonnoir .valeur', 'taux': '.entonnoir .taux', 'chiffre en carte': '.cartes .nombre', 'texte en carte': '.cartes li', 'ventilation': '.ventilation', 'statut': '.repartition dt', 'répartition': '.repartition dd', 'statut vide': '.repartition .vide dd', 'en-tête': 'thead th', 'ligne': 'tbody th', cellule: 'tbody td', 'erreur': '.badge.danger' },
	'/projet': { titre: 'h1', introduction: '.intro', 'sous-titre': 'h2', 'étape': '.etapes li', 'liste': 'main ul li', 'lien de navigation': 'header nav a' },
	'/fiche/entreprise/2': { 'terme': '.details dt', 'description': '.details dd', brouillon: '.brouillon pre', 'date': '.brouillon p', "fil d'Ariane": '.ariane a', 'page de la fiche': '.ariane [aria-current]', badge: '.details .badge' }
};

for (const theme of ['light', 'dark'] as const) {
	for (const [url, styles] of Object.entries(STYLES)) {
		test(`contraste d'au moins 4,5:1 sur ${url} en thème ${theme}`, async ({ page }) => {
			await page.emulateMedia({ colorScheme: theme });
			await page.goto(url);
			for (const [quoi, selecteur] of Object.entries(styles)) {
				expect(await page.locator(selecteur).count(), `${quoi} présent sur ${url}`).toBeGreaterThan(0);
				expect(await contraste(page, selecteur), `${quoi} sur ${url} (${theme})`).toBeGreaterThanOrEqual(4.5);
			}
			await page.screenshot({ path: `test-results/${url.replaceAll('/', '_') || 'accueil'}-${theme}.png`, fullPage: true });
		});
	}
}

for (const theme of ['light', 'dark'] as const) {
	for (const url of Object.keys(STYLES)) {
		test(`axe : aucune violation WCAG 2.1 A/AA sur ${url} en thème ${theme}`, async ({ page }) => {
			await page.emulateMedia({ colorScheme: theme });
			await page.goto(url);
			const { violations } = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze();
			const resume = violations.map((v) => `${v.id} : ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`);
			expect(resume, `violations sur ${url} (${theme})`).toEqual([]);
		});
	}
}

test('étiquettes : chaque champ de chaque page a un nom accessible, même dans les formulaires répétés', async ({ page }) => {
	const sansNom = () =>
		page.evaluate(() =>
			[...document.querySelectorAll<HTMLInputElement>('input:not([type=hidden]), select, textarea')]
				.filter((c) => !(c.labels?.length || c.getAttribute('aria-label') || c.getAttribute('aria-labelledby')))
				.map((c) => c.name || c.id || c.outerHTML.slice(0, 60))
		);
	for (const url of ['/', '/entreprises', '/offres', '/stats', '/projet', '/fiche/offre/1']) {
		await page.goto(url);
		expect(await sansNom(), `champs sans nom sur ${url}`).toEqual([]);
	}
});

test('étiquettes : pas d’identifiant en double sur le tableau (formulaires répétés)', async ({ page }) => {
	await page.goto('/');
	const doublons = await page.evaluate(() => {
		const vus = new Set<string>();
		return [...document.querySelectorAll('[id]')].map((e) => e.id).filter((id) => (vus.has(id) ? true : (vus.add(id), false)));
	});
	expect(doublons).toEqual([]);
});

test('boutons : chaque bouton a un nom unique qui dit sur quelle entreprise il agit', async ({ page }) => {
	await page.goto('/entreprises');
	const noms = await page.getByRole('button', { name: /^(Marquer .* comme contactée|Écarter .*)$/ }).evaluateAll((els) => els.map((e) => e.getAttribute('aria-label')));
	expect(noms.length).toBeGreaterThan(10);
	expect(new Set(noms).size).toBe(noms.length);
});

for (const theme of ['light', 'dark'] as const) {
	test(`axe : aucune violation avec un menu « Déplacer » ouvert, thème ${theme}`, async ({ page }) => {
		await page.emulateMedia({ colorScheme: theme });
		await page.goto('/');
		await page.getByRole('article', { name: 'Beta SA' }).getByText('Déplacer').click();
		const { violations } = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze();
		expect(violations.map((v) => `${v.id} : ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`)).toEqual([]);
		expect(await contraste(page, '.menu[open] button.btn-secondaire')).toBeGreaterThanOrEqual(4.5);
	});
}
