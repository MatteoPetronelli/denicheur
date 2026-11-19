import { expect, test } from '@playwright/test';

// Lecture seule : ce fichier passe avant suivi.spec.ts (ordre alphabétique), donc sur la base telle que semée.

test('stats : les chiffres de la base de démonstration et les exécutions', async ({ page }) => {
	await page.goto('/stats');
	await expect(page.getByRole('heading', { level: 1, name: 'Statistiques' })).toBeVisible();
	await expect(page.getByText('offres vues')).toBeVisible();
	const etape = (texte: string) => page.locator('.entonnoir li', { hasText: texte });
	await expect(etape('offres vues').locator('.nombre')).toHaveText('4');
	await expect(etape('notées par le modèle').locator('.nombre')).toHaveText('4');
	for (const t of ['retenues par le préfiltre', 'notées par le modèle', 'envoyées sur Telegram']) {
		await expect(etape(t)).toContainText("100 % des vues · 100 % de l'étape précédente");
	}
	await expect(page.locator('.cartes li', { hasText: 'exécutions enregistrées' }).locator('.nombre')).toHaveText('3');
	await expect(page.locator('.cartes li', { hasText: 'par exécution en moyenne' }).locator('.nombre')).toHaveText('6 min 50 s');
	await expect(page.locator('.cartes li', { hasText: 'de modèle au total' }).locator('.nombre')).toHaveText('20 min 30 s');

	const lignes = page.getByRole('table', { name: /dernières exécutions/ }).locator('tbody tr');
	await expect(lignes).toHaveCount(3);
	await expect(lignes.first()).toContainText('18/11/2026'); // la plus récente d'abord
	await expect(page.getByRole('row', { name: /17\/11\/2026/ })).toContainText('1 erreur, détail dans les journaux');
	await expect(page.getByRole('row', { name: /17\/11\/2026/ })).toContainText('stage');
	await expect(page.getByRole('row', { name: /17\/11\/2026/ }).locator('.badge.danger')).toHaveText('1 erreur');
	await expect(page.getByRole('row', { name: /18\/11\/2026/ }).locator('.badge.danger')).toHaveCount(0);
	await expect(page.getByText('adzuna')).toHaveCount(0); // le texte d'une erreur n'est jamais affiché
	await expect(page.getByText('HTTPError')).toHaveCount(0);

	const interessante = page.locator('.repartition > div', { has: page.locator('dt', { hasText: /^Intéressante$/ }) });
	await expect(interessante.locator('dd.offres')).toHaveText('Offres 0'); // aucune offre
	await expect(interessante.locator('dd.entreprises')).toHaveText('Entreprises 1'); // Beta SA
});

test('projet : page de présentation en français, sans donnée de la base ni donnée personnelle', async ({ page }) => {
	await page.goto('/projet');
	await expect(page.getByRole('heading', { level: 1, name: 'Le projet Dénicheur' })).toBeVisible();
	await expect(page.getByRole('heading', { level: 2 })).toHaveText(['Du signal à la candidature', 'Architecture', 'Garde-fous']);
	const texte = await page.locator('main').innerText();
	for (const valeur of ['ACME', 'Alpha Soft', 'Beta SA', 'Data Atelier', 'Petite Boîte', 'Société 01']) {
		expect(texte, `valeur de la base « ${valeur} » absente de /projet`).not.toContain(valeur);
	}
	expect(texte).not.toMatch(/[\w.+-]+@[\w-]+\.[\w.]+/);
	expect(texte).not.toMatch(/\b[A-Za-z]:[\\/]/);
	expect(texte).toContain("L'envoi reste humain");
});

test('navigation : les six pages répondent sans erreur de console ni exception', async ({ page }) => {
	const problemes: string[] = [];
	page.on('console', (m) => {
		if (m.type() === 'error') problemes.push(`console : ${m.text()}`);
	});
	page.on('pageerror', (e) => problemes.push(`exception : ${e.message}`));
	await page.goto('/');
	const nav = page.getByRole('navigation', { name: 'Pages du tableau de bord' });
	for (const nom of ['Entreprises', 'Offres', 'Statistiques', 'Projet', 'Candidatures']) {
		await nav.getByRole('link', { name: nom }).click();
		await expect(nav.getByRole('link', { name: nom })).toHaveAttribute('aria-current', 'page');
		await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
	}
	for (const url of ['/fiche/offre/1', '/fiche/entreprise/2']) {
		await page.goto(url);
		await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
	}
	expect(problemes).toEqual([]);
});

test('en-têtes : un seul titre de niveau 1 par page et aucun niveau sauté', async ({ page }) => {
	for (const url of ['/', '/entreprises', '/offres', '/stats', '/projet', '/fiche/offre/1']) {
		await page.goto(url);
		const niveaux = await page.evaluate(() => [...document.querySelectorAll('h1,h2,h3,h4')].map((h) => Number(h.tagName[1])));
		expect(niveaux.filter((n) => n === 1), `h1 sur ${url}`).toHaveLength(1);
		niveaux.forEach((n, i) => {
			if (i > 0) expect(n - niveaux[i - 1], `saut de niveau sur ${url}`).toBeLessThanOrEqual(1);
		});
	}
});
