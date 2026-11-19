import { expect, test } from '@playwright/test';

// Spec dashboard-design, en lecture seule (passe avant pages.spec.ts et suivi.spec.ts) : polices locales, petit écran.

const PAGES = ['/', '/entreprises', '/offres', '/stats', '/projet', '/fiche/entreprise/2'];

test('polices : IBM Plex chargée, et aucune requête ne quitte 127.0.0.1', async ({ page }) => {
	const hotes = new Set<string>();
	page.on('request', (r) => hotes.add(new URL(r.url()).hostname));
	for (const url of PAGES) {
		await page.goto(url);
		await page.evaluate(() => document.fonts.ready);
		const chargees = await page.evaluate(() => [...document.fonts].filter((f) => f.status === 'loaded').map((f) => f.family.replaceAll('"', '')));
		expect(chargees, `polices chargées sur ${url}`).toContain('IBM Plex Sans');
	}
	await page.goto('/stats');
	await page.evaluate(() => document.fonts.ready);
	const chargees = await page.evaluate(() => [...document.fonts].filter((f) => f.status === 'loaded').map((f) => f.family.replaceAll('"', '')));
	expect(chargees, 'police des données sur /stats').toContain('IBM Plex Mono');
	expect([...hotes].filter((h) => h !== '127.0.0.1')).toEqual([]);
});

test('petit écran : à 375 px, aucune page ne déborde horizontalement', async ({ page }) => {
	await page.setViewportSize({ width: 375, height: 812 });
	for (const url of PAGES.filter((u) => u !== '/')) {
		await page.goto(url);
		const { large, fenetre } = await page.evaluate(() => ({ large: document.documentElement.scrollWidth, fenetre: window.innerWidth }));
		expect(large, `largeur du document sur ${url}`).toBeLessThanOrEqual(fenetre);
	}
});

test('petit écran : le tableau défile dans sa zone, pas le document', async ({ page }) => {
	await page.setViewportSize({ width: 375, height: 812 });
	await page.goto('/');
	expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
	expect(await page.locator('.tableau').evaluate((e) => e.scrollWidth > e.clientWidth)).toBe(true);
	await page.screenshot({ path: 'test-results/tableau-375.png' });
});

test('listes : « — » pour une valeur absente, nombres alignés à droite, pagination numérotée', async ({ page }) => {
	await page.goto('/entreprises');
	const ligne = page.getByRole('row', { name: /^Société 01/ });
	await expect(ligne.locator('td[data-libelle="Effectif"]')).toHaveText('—');
	expect(await ligne.locator('td[data-libelle="Distance"]').evaluate((e) => getComputedStyle(e).textAlign)).toBe('end');
	const pages = page.getByRole('navigation', { name: 'Pages de la liste' });
	await expect(pages.locator('[aria-current="page"]')).toHaveText('1');
	await expect(pages.getByRole('link', { name: 'Page 2' })).toBeVisible();
});

test('offres : « sous le seuil » est un badge à part du score', async ({ page }) => {
	await page.goto('/offres');
	const cellule = page.getByRole('row', { name: /Stage support informatique/ }).locator('td[data-libelle="Score"]');
	await expect(cellule.locator('.donnee')).toHaveText('40');
	await expect(cellule.locator('.badge')).toHaveText('sous le seuil');
});

test('listes en petit écran : chaque valeur porte un libellé du <thead>', async ({ page }) => {
	await page.setViewportSize({ width: 375, height: 812 });
	for (const url of ['/entreprises', '/offres']) {
		await page.goto(url);
		const entetes = await page.locator('thead th').allTextContents();
		const libelles = await page.locator('tbody tr').first().locator('th, td').evaluateAll((els) => els.map((e) => e.getAttribute('data-libelle')));
		expect(libelles.every((l) => l !== null && entetes.includes(l)), `libellés sur ${url} : ${libelles.join(', ')}`).toBe(true);
		expect(await page.locator('tbody tr').first().evaluate((e) => getComputedStyle(e).display)).toBe('block');
	}
});

test('fiche : fil d’Ariane vers la liste, statut en badge, brouillon sans défilement à 375 px', async ({ page }) => {
	await page.goto('/fiche/entreprise/2');
	const ariane = page.getByRole('navigation', { name: "Fil d'Ariane" });
	await expect(ariane.getByRole('link', { name: 'Entreprises' })).toHaveAttribute('href', '/entreprises');
	await expect(ariane.locator('[aria-current="page"]')).toHaveText('Beta SA');
	await expect(page.locator('.details .badge')).toHaveText('Intéressante');
	await page.setViewportSize({ width: 375, height: 812 });
	await page.reload();
	expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
	expect(await page.locator('.brouillon pre').evaluate((e) => e.scrollWidth <= e.clientWidth)).toBe(true);
});
