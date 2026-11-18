import { existsSync, mkdtempSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import Database from 'better-sqlite3';
import { afterEach, describe, expect, it } from 'vitest';
import { creerBase } from './base-de-test';
import { ErreurBase, ouvrir } from './db';

const nettoyages: (() => void)[] = [];
// Dans l'ordre inverse : la connexion se ferme avant la suppression du dossier (Windows verrouille le fichier).
afterEach(() => nettoyages.splice(0).reverse().forEach((f) => f()));

function base() {
	const b = creerBase();
	nettoyages.push(b.nettoyer);
	return b.chemin;
}

describe('ouvrir', () => {
	it('ouvre une base migrée en lecture et en écriture, clés étrangères actives', () => {
		const db = ouvrir(base());
		nettoyages.push(() => db.close());
		expect(db.pragma('foreign_keys', { simple: true })).toBe(1);
		expect(db.pragma('busy_timeout', { simple: true })).toBeGreaterThanOrEqual(3000);
		expect(db.prepare('select count(*) as n from offres').get()).toEqual({ n: 0 });
		db.prepare("insert into parametres (cle, valeur) values ('essai', '1')").run();
	});

	it("refuse un fichier absent sans le créer et nomme le chemin demandé", () => {
		const chemin = join(mkdtempSync(join(tmpdir(), 'denicheur-web-')), 'absente.db');
		expect(() => ouvrir(chemin)).toThrowError(ErreurBase);
		expect(() => ouvrir(chemin)).toThrowError(/Base introuvable/);
		expect(() => ouvrir(chemin)).toThrowError(chemin);
		expect(existsSync(chemin)).toBe(false);
	});

	it('refuse une base sans le schéma attendu', () => {
		const chemin = join(mkdtempSync(join(tmpdir(), 'denicheur-web-')), 'vide.db');
		new Database(chemin).close();
		expect(() => ouvrir(chemin)).toThrowError(/Schéma inattendu/);
	});

	it("refuse un fichier qui n'est pas une base SQLite", () => {
		const chemin = join(mkdtempSync(join(tmpdir(), 'denicheur-web-')), 'texte.db');
		writeFileSync(chemin, 'pas une base, juste du texte '.repeat(50));
		expect(() => ouvrir(chemin)).toThrowError(ErreurBase);
	});
});
