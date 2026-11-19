import { afterEach, beforeEach, expect, it } from 'vitest';
import { creerBase } from '#lib/server/base-de-test.js';
import { base, fermer } from '#lib/server/db.js';
import { ajouterExecution, ajouterOffre } from '#lib/server/donnees-de-test.js';
import type { Stats } from '#lib/server/stats.js';
import { load } from './+page.server';

const AVANT = process.env.DB_PATH;
let nettoyer = () => {};

beforeEach(() => {
	const b = creerBase();
	nettoyer = b.nettoyer;
	process.env.DB_PATH = b.chemin;
});
afterEach(() => {
	fermer();
	if (AVANT === undefined) delete process.env.DB_PATH;
	else process.env.DB_PATH = AVANT;
	nettoyer();
});

it('charge les statistiques de la base', () => {
	ajouterOffre(base());
	ajouterExecution(base(), { duree_llm_s: 30 });
	const { stats } = load({} as Parameters<typeof load>[0]) as unknown as { stats: Stats };
	expect(stats.offres.vues).toBe(1);
	expect(stats.llm.total_s).toBe(30);
});

it('base vide : la page rendue ne contient ni NaN ni Infinity', async () => {
	const { render } = await import('svelte/server');
	const { default: Page } = await import('./+page.svelte');
	const data = load({} as Parameters<typeof load>[0]) as unknown as { stats: Stats };
	const { body } = render(Page, { props: { data, form: undefined, params: {} } as never });
	expect(body).toContain('offres vues');
	expect(body).not.toMatch(/NaN|Infinity/);
});
