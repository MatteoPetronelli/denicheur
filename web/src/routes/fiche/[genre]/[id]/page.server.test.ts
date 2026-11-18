import { afterEach, beforeEach, expect, it } from 'vitest';
import { creerBase } from '#lib/server/base-de-test.js';
import { base, fermer } from '#lib/server/db.js';
import { ajouterEntreprise, ajouterOffre } from '#lib/server/donnees-de-test.js';
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

const charger = (genre: string, id: string) => load({ params: { genre, id } } as Parameters<typeof load>[0]);

it('charge la fiche d’une offre et d’une entreprise', () => {
	const o = ajouterOffre(base(), { titre: 'Dev' });
	const e = ajouterEntreprise(base(), { nom: 'Beta' });
	expect(charger('offre', String(o))).toMatchObject({ carte: { titre: 'Dev' } });
	expect(charger('entreprise', String(e))).toMatchObject({ carte: { titre: 'Beta' } });
});

it.each([
	['autre', '1'],
	['offre', 'abc'],
	['offre', '0'],
	['offre', '1.5'],
	['offre', '999'],
	['entreprise', '999']
])('répond 404 pour %s %s', (genre, id) => {
	ajouterOffre(base());
	ajouterEntreprise(base()); // « autre/1 » ne doit pas retomber sur l’entreprise 1
	expect(() => charger(genre, id)).toThrowError(expect.objectContaining({ status: 404 }));
});
