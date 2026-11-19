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
