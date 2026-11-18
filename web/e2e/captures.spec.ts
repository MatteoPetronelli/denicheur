import { resolve } from 'node:path';
import { expect, test, type Page } from '@playwright/test';

// Captures du README, prises sur la base de démonstration synthétique (aucun nom réel) : `npm run captures`.
const DOSSIER = resolve(import.meta.dirname, '../../docs/captures');
const TAILLE = { width: 1280, height: 760 };

async function deplacer(page: Page, titre: string, statut: string) {
	const carte = page.getByRole('article', { name: titre });
	await carte.getByLabel('Passer à').selectOption({ label: statut });
	await carte.getByRole('button', { name: 'Changer' }).click();
	await expect(page.getByRole('status')).toBeVisible();
}

test.use({ viewport: TAILLE });

test('captures du tableau de bord', async ({ page }) => {
	await page.goto('/');
	await deplacer(page, 'Développeur web en alternance', 'Candidature envoyée');
	await deplacer(page, 'Stage analyse de données', 'Intéressante');
	await page.evaluate(() => window.scrollTo(0, 0));
	await page.screenshot({ path: `${DOSSIER}/tableau.png` });

	await page.goto('/entreprises');
	await page.getByRole('button', { name: 'Marquer Alpha Soft comme contactée' }).click();
	await expect(page.getByRole('status')).toBeVisible();
	await page.evaluate(() => window.scrollTo(0, 0));
	await page.screenshot({ path: `${DOSSIER}/entreprises.png` });

	await page.goto('/offres');
	await page.screenshot({ path: `${DOSSIER}/offres.png` });

	await page.goto('/stats');
	await page.screenshot({ path: `${DOSSIER}/statistiques.png`, fullPage: true });

	await page.goto('/fiche/entreprise/2');
	await page.screenshot({ path: `${DOSSIER}/fiche.png` });
});
