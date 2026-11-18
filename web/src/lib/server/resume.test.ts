import { afterEach, expect, it } from 'vitest';
import { creerBase } from './base-de-test';
import { ouvrir } from './db';
import { resume } from './resume';

const nettoyages: (() => void)[] = [];
afterEach(() => nettoyages.splice(0).reverse().forEach((f) => f()));

function ouverte() {
	const b = creerBase();
	nettoyages.push(b.nettoyer);
	const db = ouvrir(b.chemin);
	nettoyages.push(() => db.close());
	return db;
}

it('compte zéro partout sur une base vide', () => {
	expect(resume(ouverte())).toEqual({ offres: 0, entreprises: 0, suivis: 0 });
});

it('compte les offres, les entreprises et les lignes de suivi', () => {
	const db = ouverte();
	const ajouter = db.prepare(
		"insert into entreprises (siret, nom, origine, cree_le, maj_le) values (?, ?, 'csv', '2026-11-18 09:00:00.000000', '2026-11-18 09:00:00.000000')"
	);
	ajouter.run('00000000100011', 'A');
	ajouter.run('00000000200011', 'B');
	db.prepare(
		"insert into candidatures (entreprise_id, statut, cree_le, maj_le) values (1, 'interessante', '2026-11-18 09:00:00.000000', '2026-11-18 09:00:00.000000')"
	).run();
	expect(resume(db)).toEqual({ offres: 0, entreprises: 2, suivis: 1 });
});
