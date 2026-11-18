import { afterEach, describe, expect, it } from 'vitest';
import { creerBase } from '#lib/server/base-de-test.js';
import { fermer } from '#lib/server/db.js';
import { load } from './+layout.server';

const AVANT = process.env.DB_PATH;
const nettoyages: (() => void)[] = [];
afterEach(() => {
	fermer();
	if (AVANT === undefined) delete process.env.DB_PATH;
	else process.env.DB_PATH = AVANT;
	nettoyages.splice(0).reverse().forEach((f) => f());
});

describe('layout : état de la base', () => {
	it('répond 503 avec « Base introuvable » et le chemin demandé quand la base manque', () => {
		process.env.DB_PATH = 'C:/nulle/part/absente.db';
		let erreur: unknown;
		try {
			load({} as Parameters<typeof load>[0]);
		} catch (e) {
			erreur = e;
		}
		expect(erreur).toMatchObject({ status: 503, body: { message: expect.stringContaining('Base introuvable') } });
		expect(erreur).toMatchObject({ body: { message: expect.stringContaining('absente.db') } });
	});

	it('laisse passer quand la base est valide', () => {
		const b = creerBase();
		nettoyages.push(b.nettoyer);
		process.env.DB_PATH = b.chemin;
		expect(() => load({} as Parameters<typeof load>[0])).not.toThrow();
	});
});
