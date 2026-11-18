import { expect, test } from '@playwright/test';

test('le tableau est en français, avec navigation et titre', async ({ page }) => {
	await page.goto('/');
	await expect(page.getByRole('heading', { level: 1, name: 'Candidatures' })).toBeVisible();
	expect(await page.locator('html').getAttribute('lang')).toBe('fr');
	await expect(page).toHaveTitle(/Candidatures/);
	const nav = page.getByRole('navigation', { name: 'Pages du tableau de bord' });
	for (const nom of ['Candidatures', 'Entreprises', 'Offres']) await expect(nav.getByRole('link', { name: nom })).toBeVisible();
	await expect(nav.getByRole('link', { name: 'Candidatures' })).toHaveAttribute('aria-current', 'page');
});

test('clavier : lien d’évitement, puis focus visible sur les premiers contrôles', async ({ page }) => {
	await page.goto('/');
	await page.keyboard.press('Tab');
	const evitement = page.getByRole('link', { name: 'Aller au contenu' });
	await expect(evitement).toBeFocused();
	await expect(evitement).toBeInViewport();
	await page.keyboard.press('Enter');
	await expect(page).toHaveURL(/#contenu$/);

	await page.goto('/offres');
	for (let i = 0; i < 6; i++) {
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

test('une fiche inconnue répond 404', async ({ page }) => {
	const reponse = await page.goto('/fiche/offre/9999');
	expect(reponse?.status()).toBe(404);
	await expect(page.getByRole('alert')).toContainText('Fiche introuvable');
});

test('l’hôte étranger est refusé', async ({ request }) => {
	const reponse = await request.get('/', { headers: { host: 'exemple.fr' } });
	expect(reponse.status()).toBe(403);
});
