import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterEach, expect, it } from 'vitest';
import { cheminConfig, ErreurConfig, lireScoreMin } from './config.js';

const dossiers: string[] = [];
afterEach(() => dossiers.splice(0).forEach((d) => rmSync(d, { recursive: true, force: true })));

function fichier(contenu: string): string {
	const d = mkdtempSync(join(tmpdir(), 'denicheur-cfg-'));
	dossiers.push(d);
	const chemin = join(d, 'recherches.yaml');
	writeFileSync(chemin, contenu, 'utf-8');
	return chemin;
}

it('lit score_min dans la configuration', () => {
	expect(lireScoreMin(fichier('age_max_jours: 30\nscore_min: 65\nautre: 1\n'))).toBe(65);
	expect(lireScoreMin(fichier('score_min: 0\n'))).toBe(0);
});

it('un fichier absent donne une erreur française avec le chemin', () => {
	const chemin = join(tmpdir(), 'nulle-part-recherches.yaml');
	expect(() => lireScoreMin(chemin)).toThrowError(ErreurConfig);
	expect(() => lireScoreMin(chemin)).toThrowError(/Configuration introuvable/);
	expect(() => lireScoreMin(chemin)).toThrowError(chemin);
});

it.each([['age_max_jours: 30\n'], ['score_min: beaucoup\n'], ['score_min: 120\n'], ['score_min: -1\n'], ['score_min: 6.5\n'], ['- liste\n'], ['']])(
	'un score_min absent ou invalide est refusé : %j',
	(contenu) => {
		expect(() => lireScoreMin(fichier(contenu))).toThrowError(/score_min/);
	}
);

it('un YAML illisible est refusé sans reprendre son contenu', () => {
	expect(() => lireScoreMin(fichier('score_min: [65\nmot_de_passe: secret'))).toThrowError(ErreurConfig);
	try {
		lireScoreMin(fichier('score_min: [65\nmot_de_passe: secret'));
	} catch (e) {
		expect((e as Error).message).not.toContain('secret');
	}
});

it('le chemin de la configuration vient de CONFIG_PATH, sinon du dossier voisin du tableau', () => {
	const avant = process.env.CONFIG_PATH;
	try {
		process.env.CONFIG_PATH = join(tmpdir(), 'autre.yaml');
		expect(cheminConfig()).toBe(join(tmpdir(), 'autre.yaml'));
		delete process.env.CONFIG_PATH;
		expect(cheminConfig().replaceAll('\\', '/')).toMatch(/\/config\/recherches\.yaml$/);
	} finally {
		if (avant === undefined) delete process.env.CONFIG_PATH;
		else process.env.CONFIG_PATH = avant;
	}
});
