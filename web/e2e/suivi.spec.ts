import { expect, test } from '@playwright/test';

// Scénario sur la base de démonstration recréée au lancement (voir graine.ts) : ce fichier modifie la base,
// il passe donc en dernier (ordre alphabétique, un seul processus).

test('tableau : « Nouvelles », colonnes et cartes avec score, distance et entreprise', async ({ page }) => {
	await page.goto('/');
	await expect(page.getByRole('heading', { level: 2, name: 'Nouvelles (4)' })).toBeVisible();
	await expect(page.getByRole('heading', { level: 2, name: 'Intéressante (1)' })).toBeVisible(); // Beta SA, entreprise
	const carte = page.getByRole('article', { name: 'Développeur web en alternance' });
	await expect(carte).toContainText('ACME');
	await expect(carte).toContainText('Score 82');
	await expect(carte).toContainText('12 km');
	const entreprise = page.getByRole('article', { name: 'Beta SA' });
	await expect(entreprise).toContainText('Conseil en systèmes');
	await expect(entreprise).toContainText('Priorité 2');
	await page.screenshot({ path: 'test-results/tableau-avant.png', fullPage: true });
});

test('colonnes : une colonne vide est plus étroite que « Nouvelles », et garde son libellé et son effectif', async ({ page }) => {
	await page.goto('/');
	const largeur = (id: string) => page.locator(`section:has(> h2#${id})`).evaluate((e) => e.getBoundingClientRect().width);
	await expect(page.getByRole('heading', { level: 2, name: 'Relancée (0)' })).toBeVisible();
	expect(await largeur('col-relancee')).toBeLessThan(await largeur('col-nouvelles'));
});

test('carte : un clic hors des liens ouvre la fiche, le lien externe ne l’ouvre pas', async ({ page, context }) => {
	await page.goto('/');
	const carte = page.getByRole('article', { name: 'Développeur full stack' });
	const boite = (await carte.boundingBox())!;
	const [onglet] = await Promise.all([context.waitForEvent('page'), carte.getByRole('link', { name: "Voir l'offre" }).click()]);
	await onglet.close();
	await expect(page).toHaveURL(/\/$/);
	await page.mouse.click(boite.x + boite.width - 6, boite.y + 6); // coin haut-droit, hors du titre
	await expect(page).toHaveURL(/\/fiche\/offre\/\d+$/);
});

test('carte : le niveau du score est écrit, pas seulement coloré', async ({ page }) => {
	await page.goto('/');
	const score = (titre: string) => page.getByRole('article', { name: titre }).getByRole('listitem').filter({ hasText: 'Score' });
	await expect(score('Stage support informatique')).toHaveText('Score 40 · sous le seuil');
	await expect(score('Développeur web en alternance')).toHaveText('Score 82 · fort');
	await expect(score('Stage analyse de données')).toHaveText('Score 70');
});

test('menu : une carte « Intéressante » ne propose que « Candidature envoyée » et « Écartée »', async ({ page }) => {
	await page.goto('/');
	const carte = page.getByRole('article', { name: 'Beta SA' });
	await carte.getByText('Déplacer').click();
	await expect(carte.getByRole('button')).toHaveText(['Candidature envoyée', 'Écartée']);
});

test('menu : ouvrir un menu ferme les autres', async ({ page }) => {
	await page.goto('/');
	await page.getByRole('article', { name: 'Beta SA' }).getByText('Déplacer').click();
	await page.getByRole('article', { name: 'Développeur full stack' }).getByText('Déplacer').click();
	await expect(page.locator('details.menu[open]')).toHaveCount(1);
});

test('déplacer une carte au clavier : message, focus sur la carte, statut conservé après rechargement', async ({ page }) => {
	await page.goto('/');
	await page.getByRole('article', { name: 'Développeur web en alternance' }).getByText('Déplacer').focus();
	await page.keyboard.press('Enter');
	await page.keyboard.press('Tab');
	await expect(page.getByRole('button', { name: 'Passer « Développeur web en alternance » à Intéressante' })).toBeFocused();
	await page.keyboard.press('Tab');
	await page.keyboard.press('Enter'); // Candidature envoyée
	await expect(page.getByRole('status')).toHaveText('« Développeur web en alternance » passée à Candidature envoyée.');
	await expect(page.getByRole('heading', { level: 2, name: 'Candidature envoyée (1)' })).toBeVisible();
	await expect(page.getByRole('heading', { level: 2, name: 'Nouvelles (3)' })).toBeVisible();
	expect(await page.evaluate(() => document.activeElement?.id)).toMatch(/^carte-offre-\d+$/);
	await expect(page.locator(':focus')).toHaveAccessibleName('Développeur web en alternance');
	await page.reload();
	await expect(page.getByRole('heading', { level: 2, name: 'Candidature envoyée (1)' })).toBeVisible();
	await page.screenshot({ path: 'test-results/tableau-apres.png', fullPage: true });
});

test('déplacer une carte à la souris, puis le statut final n’offre plus que « Écartée »', async ({ page }) => {
	await page.goto('/');
	const carte = page.getByRole('article', { name: 'Développeur web en alternance' });
	await carte.getByText('Déplacer').click();
	await carte.getByRole('button', { name: /à Entretien$/ }).click();
	await expect(page.getByRole('heading', { level: 2, name: 'Entretien (1)' })).toBeVisible();
	const deplacee = page.getByRole('article', { name: 'Développeur web en alternance' });
	await deplacee.getByText('Déplacer').click();
	await expect(deplacee.getByRole('button')).toHaveText(['Écartée']);
});

test('« Beta SA » déplacée : message et focus, puis la dernière colonne est atteinte au clavier', async ({ page }) => {
	await page.goto('/');
	await page.getByRole('article', { name: 'Beta SA' }).getByText('Déplacer').click();
	await page.getByRole('button', { name: 'Passer « Beta SA » à Candidature envoyée' }).click();
	await expect(page.getByRole('status')).toContainText('Beta SA');
	await expect(page.getByRole('status')).toContainText('Candidature envoyée');
	expect(await page.evaluate(() => document.activeElement?.id)).toMatch(/^carte-entreprise-\d+$/);

	await page.getByRole('article', { name: 'Beta SA' }).getByText('Déplacer').click();
	await page.getByRole('button', { name: 'Passer « Beta SA » à Sans réponse' }).click();
	await expect(page.getByRole('heading', { level: 2, name: 'Sans réponse (1)' })).toBeVisible();
	await page.goto('/');
	const titre = page.locator('section:has(> h2#col-sans_reponse)').getByRole('link', { name: 'Beta SA' });
	for (let i = 0; i < 80 && !(await titre.evaluate((e) => e === document.activeElement)); i++) await page.keyboard.press('Tab');
	await expect(titre).toBeFocused();
	await expect(titre).toBeInViewport();
});

test('filtres : stage seulement, puis entreprises seulement', async ({ page }) => {
	await page.goto('/');
	await page.getByLabel('Piste').selectOption('stage');
	await page.getByRole('button', { name: 'Filtrer' }).click();
	await expect(page).toHaveURL(/piste=stage/);
	await expect(page.getByRole('article', { name: 'Stage analyse de données' })).toBeVisible();
	await expect(page.getByRole('article', { name: 'Beta SA' })).toHaveCount(0);
	await expect(page.getByRole('article', { name: 'Développeur full stack' })).toHaveCount(0);

	await page.goto('/?nature=entreprise');
	await expect(page.getByRole('article', { name: 'Beta SA' })).toBeVisible();
	await expect(page.getByRole('article', { name: 'Stage analyse de données' })).toHaveCount(0);
});

test('un filtre reste actif après un changement de statut', async ({ page }) => {
	await page.goto('/?piste=stage');
	const carte = page.getByRole('article', { name: 'Stage analyse de données' });
	await carte.getByText('Déplacer').click();
	await carte.getByRole('button', { name: /à Intéressante$/ }).click();
	await expect(page.getByRole('status')).toBeVisible();
	await expect(page).toHaveURL(/piste=stage/);
	await expect(page.getByRole('article', { name: 'Développeur full stack' })).toHaveCount(0);
});

test('écartées : masquées, puis affichées à la demande', async ({ page }) => {
	await page.goto('/');
	const carte = page.getByRole('article', { name: 'Stage support informatique' });
	await carte.getByText('Déplacer').click();
	await carte.getByRole('button', { name: /à Écartée$/ }).click();
	await expect(page.getByRole('article', { name: 'Stage support informatique' })).toHaveCount(0);
	await page.getByLabel(/Afficher les écartées/).check();
	await page.getByRole('button', { name: 'Filtrer' }).click();
	await expect(page.getByRole('heading', { level: 2, name: 'Écartées (1)' })).toBeVisible();
	await expect(page.getByRole('article', { name: 'Stage support informatique' })).toBeVisible();
});

test('entreprises : tri, pagination, offre ouverte du même SIRET, puis « Contactée »', async ({ page }) => {
	await page.goto('/entreprises');
	await expect(page.getByText('60 entreprises · page 1 sur 2')).toBeVisible();
	const lignes = page.locator('tbody tr');
	await expect(lignes.first()).toContainText('Alpha Soft'); // priorité 1
	await expect(lignes).toHaveCount(50);
	await expect(page.getByRole('row', { name: /Beta SA/ })).toContainText('Développeur full stack'); // même SIRET
	await expect(page.getByRole('row', { name: /Société 01/ })).not.toContainText('Développeur'); // aucun rapprochement par nom

	await page.getByRole('link', { name: 'Page suivante' }).click();
	await expect(page).toHaveURL(/page=2/);
	await expect(page.getByText('60 entreprises · page 2 sur 2')).toBeVisible();
	await expect(page.locator('tbody tr')).toHaveCount(10);
	await page.getByRole('link', { name: 'Page précédente' }).click();

	await page.getByRole('button', { name: 'Marquer Alpha Soft comme contactée' }).click();
	await expect(page.getByRole('status')).toHaveText('Statut mis à jour.');
	const alpha = page.getByRole('row', { name: /Alpha Soft/ });
	await expect(alpha).toContainText('Candidature envoyée');
	await expect(alpha.getByRole('button', { name: /comme contactée/ })).toHaveCount(0);
	await expect(alpha).toContainText('/20'); // date de contact en français (jj/mm/aaaa)
	await page.screenshot({ path: 'test-results/entreprises.png', fullPage: true });
});

test('entreprises : « sans suivi » et recherche par nom', async ({ page }) => {
	await page.goto('/entreprises');
	await page.getByLabel('Statut').selectOption('sans_suivi');
	await page.getByLabel('Nom').fill('société 5');
	await page.getByRole('button', { name: 'Filtrer' }).click();
	await expect(page.locator('tbody tr')).toHaveCount(9); // Société 50 à 58 (« Société 05 » ne contient pas « société 5 »)
	await expect(page.getByRole('row', { name: /Alpha Soft/ })).toHaveCount(0);
});

test('entreprises : « Écartée » la retire de « sans suivi »', async ({ page }) => {
	await page.goto('/entreprises?statut=sans_suivi');
	await page.getByRole('button', { name: 'Écarter Société 01' }).click();
	await expect(page.getByRole('status')).toBeVisible();
	await expect(page.getByRole('row', { name: /Société 01/ })).toHaveCount(0);
	await page.goto('/entreprises?statut=ignoree');
	await expect(page.getByRole('row', { name: /Société 01/ })).toContainText('Écartée');
});

test('fiche : le texte d’un brouillon est affiché tel quel, sans exécuter son code', async ({ page }) => {
	await page.goto('/fiche/entreprise/2');
	await expect(page.getByRole('heading', { level: 1, name: 'Beta SA' })).toBeVisible();
	await expect(page.getByRole('heading', { level: 3, name: 'Message spontané' })).toBeVisible();
	await expect(page.locator('.brouillon pre')).toContainText('<script>window.__xss = 1</script>');
	expect(await page.evaluate(() => (window as unknown as { __xss?: number }).__xss)).toBeUndefined();
	await expect(page.getByRole('link', { name: 'Développeur full stack' })).toBeVisible(); // offre ouverte
	await page.screenshot({ path: 'test-results/fiche.png', fullPage: true });
});

test('offres : les offres sous le seuil sont marquées, le filtre « sous le seuil » les isole', async ({ page }) => {
	await page.goto('/offres');
	await expect(page.getByText('Seuil de score de la configuration : 65')).toBeVisible();
	await expect(page.getByRole('row', { name: /Stage support informatique/ })).toContainText('sous le seuil');
	await expect(page.getByRole('row', { name: /Développeur full stack/ })).not.toContainText('sous le seuil');
	await page.getByLabel('Score').selectOption('sous');
	await page.getByRole('button', { name: 'Filtrer' }).click();
	await expect(page.locator('tbody tr')).toHaveCount(1);
	await page.screenshot({ path: 'test-results/offres.png', fullPage: true });
});

test('envoi : le bouton est occupé pendant la requête, puis plus rien n’est occupé', async ({ page }) => {
	await page.goto('/entreprises');
	let liberer = () => {};
	const attente = new Promise<void>((r) => (liberer = r));
	await page.route((u) => u.search.includes('/statut'), async (route) => {
		await attente;
		await route.continue();
	});
	const bouton = page.getByRole('button', { name: 'Marquer Société 06 comme contactée' });
	await bouton.click();
	await expect(bouton).toHaveAttribute('aria-busy', 'true');
	await expect(bouton).toBeDisabled();
	liberer();
	await expect(page.getByRole('status')).toBeVisible();
	await expect(page.getByRole('row', { name: /Société 06/ })).toContainText('Candidature envoyée');
	await expect(page.locator('[aria-busy]')).toHaveCount(0);
});

test.describe('sans JavaScript', () => {
	test.use({ javaScriptEnabled: false });

	test('un changement de statut recharge la page avec le résultat', async ({ page }) => {
		await page.goto('/entreprises');
		await page.getByRole('button', { name: 'Marquer Société 05 comme contactée' }).click();
		await expect(page.getByRole('status')).toHaveText('Statut mis à jour.');
		await expect(page.getByRole('row', { name: /Société 05/ })).toContainText('Candidature envoyée');
	});
});

test.describe('sans JavaScript, sur le tableau', () => {
	test.use({ javaScriptEnabled: false });

	test('le menu « Déplacer » recharge la page avec la carte dans sa nouvelle colonne', async ({ page }) => {
		await page.goto('/');
		const carte = page.getByRole('article', { name: 'Développeur full stack' });
		await carte.getByText('Déplacer').click();
		await carte.getByRole('button', { name: /à Intéressante$/ }).click();
		await expect(page.locator('section:has(> h2#col-interessante)').getByRole('article', { name: 'Développeur full stack' })).toBeVisible();
	});
});
