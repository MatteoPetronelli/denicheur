import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterEach, beforeEach, expect, it } from 'vitest';
import { creerBase } from '#lib/server/base-de-test.js';
import { base, fermer } from '#lib/server/db.js';
import { ajouterOffre, ajouterScore } from '#lib/server/donnees-de-test.js';
import type { ListeOffres } from '#lib/server/offres.js';
import { load } from './+page.server';

const AVANT = { db: process.env.DB_PATH, cfg: process.env.CONFIG_PATH };
let nettoyages: (() => void)[] = [];

beforeEach(() => {
	const b = creerBase();
	const dossier = mkdtempSync(join(tmpdir(), 'denicheur-cfg-'));
	writeFileSync(join(dossier, 'recherches.yaml'), 'score_min: 65\n', 'utf-8');
	process.env.DB_PATH = b.chemin;
	process.env.CONFIG_PATH = join(dossier, 'recherches.yaml');
	nettoyages = [b.nettoyer, () => rmSync(dossier, { recursive: true, force: true })];
});

afterEach(() => {
	fermer();
	for (const [cle, valeur] of [['DB_PATH', AVANT.db], ['CONFIG_PATH', AVANT.cfg]] as const) {
		if (valeur === undefined) delete process.env[cle];
		else process.env[cle] = valeur;
	}
	nettoyages.forEach((f) => f());
});

const charger = (recherche = '') =>
	load({ url: new URL(`http://127.0.0.1/offres${recherche}`) } as Parameters<typeof load>[0]) as unknown as {
		scoreMin: number;
		liste: ListeOffres;
		filtres: { seuil?: string };
	};

it('applique le seuil de la configuration et marque les offres sous le seuil', () => {
	const a = ajouterOffre(base(), { titre: 'Bonne' });
	const b = ajouterOffre(base(), { titre: 'Faible' });
	ajouterScore(base(), a, 80);
	ajouterScore(base(), b, 40);
	const data = charger('?seuil=sous');
	expect(data.scoreMin).toBe(65);
	expect(data.liste.lignes.map((l) => [l.titre, l.sousSeuil])).toEqual([['Faible', true]]);
});

it('une configuration absente donne une erreur 500 en français', () => {
	process.env.CONFIG_PATH = join(tmpdir(), 'absente-recherches.yaml');
	let erreur: unknown;
	try {
		charger();
	} catch (e) {
		erreur = e;
	}
	expect(erreur).toMatchObject({
		status: 500,
		body: { message: expect.stringContaining('Configuration introuvable') }
	});
});
