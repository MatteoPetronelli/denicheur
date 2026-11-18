import { afterEach, describe, expect, it } from 'vitest';
import { creerBase } from './base-de-test.js';
import { ouvrir } from './db.js';
import { ajouterEntreprise, ajouterOffre, ajouterScore } from './donnees-de-test.js';
import { listeOffres } from './offres.js';
import { changerStatut } from './suivi.js';

const T0 = new Date('2026-11-18T09:00:00.000Z');
const nettoyages: (() => void)[] = [];
afterEach(() => nettoyages.splice(0).reverse().forEach((f) => f()));

function ouverte() {
	const b = creerBase();
	nettoyages.push(b.nettoyer);
	const db = ouvrir(b.chemin);
	nettoyages.push(() => db.close());
	return db;
}

const titres = (r: { lignes: { titre: string }[] }) => r.lignes.map((l) => l.titre);

function noter(db: ReturnType<typeof ouverte>, titre: string, score: number, o: Parameters<typeof ajouterOffre>[1] = {}) {
	const id = ajouterOffre(db, { titre, ...o });
	ajouterScore(db, id, score, o.piste === 'stage' ? 'stage' : 'alternance');
	return id;
}

describe('listeOffres', () => {
	it('liste par score décroissant, y compris sous le seuil, marquées ; le seuil lui-même est atteint', () => {
		const db = ouverte();
		noter(db, 'Bonne', 82);
		noter(db, 'Limite', 65);
		noter(db, 'Faible', 40);
		const r = listeOffres(db, 65, {});
		expect(r.lignes.map((l) => [l.titre, l.score, l.sousSeuil])).toEqual([
			['Bonne', 82, false],
			['Limite', 65, false],
			['Faible', 40, true]
		]);
	});

	it('exclut les offres rejetées par le préfiltre et celles qui n’ont pas de score', () => {
		const db = ouverte();
		noter(db, 'Retenue', 70);
		noter(db, 'Rejetée', 90, { motif_rejet: 'niveau' });
		ajouterOffre(db, { titre: 'Sans score' });
		expect(titres(listeOffres(db, 65, {}))).toEqual(['Retenue']);
	});

	it('à score égal, l’offre la plus ancienne d’abord', () => {
		const db = ouverte();
		noter(db, 'A', 70);
		noter(db, 'B', 70);
		expect(titres(listeOffres(db, 65, {}))).toEqual(['A', 'B']);
	});

	it('filtre par piste', () => {
		const db = ouverte();
		noter(db, 'Stage', 70, { piste: 'stage' });
		noter(db, 'Alternance', 70, { piste: 'alternance' });
		noter(db, 'Autre', 70, { piste: 'autre' });
		expect(titres(listeOffres(db, 65, { piste: 'stage' }))).toEqual(['Stage']);
		expect(titres(listeOffres(db, 65, { piste: 'alternance' }))).toEqual(['Alternance']);
		expect(titres(listeOffres(db, 65, {})).sort()).toEqual(['Alternance', 'Autre', 'Stage']);
	});

	it('filtre par seuil : atteint ou sous le seuil', () => {
		const db = ouverte();
		noter(db, 'Haut', 80);
		noter(db, 'Pile', 65);
		noter(db, 'Bas', 64);
		expect(titres(listeOffres(db, 65, { seuil: 'atteint' }))).toEqual(['Haut', 'Pile']);
		expect(titres(listeOffres(db, 65, { seuil: 'sous' }))).toEqual(['Bas']);
	});

	it('montre le statut de suivi, ou aucun, et un lien sûr', () => {
		const db = ouverte();
		const a = noter(db, 'Suivie', 80, { url: 'https://x.test/a' });
		noter(db, 'Libre', 70, { url: 'javascript:alert(1)' });
		changerStatut(db, { type: 'offre', id: a }, 'candidature_envoyee', T0);
		expect(listeOffres(db, 65, {}).lignes.map((l) => [l.titre, l.statut, l.lien])).toEqual([
			['Suivie', 'candidature_envoyee', 'https://x.test/a'],
			['Libre', null, null]
		]);
	});

	it('une entreprise suivie sans offre ne gêne rien', () => {
		const db = ouverte();
		noter(db, 'Une', 70);
		const e = ajouterEntreprise(db);
		changerStatut(db, { type: 'entreprise', id: e }, 'interessante', T0);
		expect(titres(listeOffres(db, 65, {}))).toEqual(['Une']);
	});

	it('pagine par 50', () => {
		const db = ouverte();
		for (let i = 0; i < 120; i++) noter(db, `O${i}`, 99 - (i % 30));
		const p3 = listeOffres(db, 65, { page: 3 });
		expect([p3.total, p3.pages, p3.page, p3.lignes.length]).toEqual([120, 3, 3, 20]);
		expect(listeOffres(db, 65, { page: 50 }).page).toBe(3);
	});
});
