import { afterEach, describe, expect, it } from 'vitest';
import { creerBase } from './base-de-test.js';
import { ouvrir } from './db.js';
import { ajouterBrouillon, ajouterEntreprise, ajouterOffre } from './donnees-de-test.js';
import { listeEntreprises, offresOuvertesDuSiret } from './entreprises.js';
import { changerStatut } from './suivi.js';

const nettoyages: (() => void)[] = [];
afterEach(() => nettoyages.splice(0).reverse().forEach((f) => f()));

function ouverte() {
	const b = creerBase();
	nettoyages.push(b.nettoyer);
	const db = ouvrir(b.chemin);
	nettoyages.push(() => db.close());
	return db;
}

const SIRET = '12345678900011';

describe('offresOuvertesDuSiret', () => {
	it('rapproche par SIRET exact seulement, jamais par le nom', () => {
		const db = ouverte();
		ajouterOffre(db, { titre: 'Même SIRET', entreprise: 'ACME', siret: SIRET });
		ajouterOffre(db, { titre: 'Même nom, autre SIRET', entreprise: 'ACME', siret: '99999999900011' });
		ajouterOffre(db, { titre: 'Même nom, sans SIRET', entreprise: 'ACME', siret: null });
		expect(offresOuvertesDuSiret(db, SIRET).map((o) => o.titre)).toEqual(['Même SIRET']);
	});

	it('écarte les offres rejetées par le préfiltre, les plus récentes d’abord, trois au plus', () => {
		const db = ouverte();
		for (let i = 1; i <= 4; i++) ajouterOffre(db, { titre: `O${i}`, siret: SIRET });
		ajouterOffre(db, { titre: 'Rejetée', siret: SIRET, motif_rejet: 'niveau' }); // la plus récente
		expect(offresOuvertesDuSiret(db, SIRET).map((o) => o.titre)).toEqual(['O4', 'O3', 'O2']);
	});
});

// --- liste des entreprises ---
const T0 = new Date('2026-11-18T09:00:00.000Z');
const noms = (r: { lignes: { nom: string }[] }) => r.lignes.map((l) => l.nom);

describe('listeEntreprises : tri', () => {
	it('priorité croissante, priorités nulles à la fin, puis distance, puis identifiant', () => {
		const db = ouverte();
		ajouterEntreprise(db, { nom: 'Sans priorité loin', priorite: null, distance_km: 30 });
		ajouterEntreprise(db, { nom: 'P2', priorite: 2, distance_km: 5 });
		ajouterEntreprise(db, { nom: 'P1 loin', priorite: 1, distance_km: 20 });
		ajouterEntreprise(db, { nom: 'P1 près', priorite: 1, distance_km: 3 });
		ajouterEntreprise(db, { nom: 'Sans priorité près', priorite: null, distance_km: 2 });
		ajouterEntreprise(db, { nom: 'Sans priorité ni distance', priorite: null, distance_km: null });
		expect(noms(listeEntreprises(db, {}))).toEqual([
			'P1 près',
			'P1 loin',
			'P2',
			'Sans priorité près',
			'Sans priorité loin',
			'Sans priorité ni distance'
		]);
	});
});

describe('listeEntreprises : filtres', () => {
	function jeu() {
		const db = ouverte();
		const a = ajouterEntreprise(db, { nom: 'Alpha', priorite: 1 });
		const b = ajouterEntreprise(db, { nom: 'Beta', priorite: 2 });
		const c = ajouterEntreprise(db, { nom: 'Gamma', priorite: 3 });
		ajouterEntreprise(db, { nom: 'Delta', priorite: 4 });
		changerStatut(db, { type: 'entreprise', id: a }, 'candidature_envoyee', T0);
		changerStatut(db, { type: 'entreprise', id: b }, 'ignoree', T0);
		changerStatut(db, { type: 'entreprise', id: c }, 'interessante', T0);
		return db;
	}

	it('« sans suivi » : seulement les entreprises sans ligne de suivi', () => {
		expect(noms(listeEntreprises(jeu(), { statut: 'sans_suivi' }))).toEqual(['Delta']);
	});

	it('un statut précis', () => {
		const db = jeu();
		expect(noms(listeEntreprises(db, { statut: 'candidature_envoyee' }))).toEqual(['Alpha']);
		expect(noms(listeEntreprises(db, { statut: 'ignoree' }))).toEqual(['Beta']);
		expect(noms(listeEntreprises(db, { statut: 'interessante' }))).toEqual(['Gamma']);
	});

	it('sans filtre : toutes, avec leur statut', () => {
		const r = listeEntreprises(jeu(), {});
		expect(r.lignes.map((l) => [l.nom, l.statut])).toEqual([
			['Alpha', 'candidature_envoyee'],
			['Beta', 'ignoree'],
			['Gamma', 'interessante'],
			['Delta', null]
		]);
	});

	it('recherche sur le nom sans tenir compte de la casse', () => {
		const db = jeu();
		expect(noms(listeEntreprises(db, { q: 'ALP' }))).toEqual(['Alpha']);
		expect(noms(listeEntreprises(db, { q: 'a' })).sort()).toEqual(['Alpha', 'Beta', 'Delta', 'Gamma']);
	});

	it('« % » et « _ » dans la recherche sont du texte, pas des jokers', () => {
		const db = ouverte();
		ajouterEntreprise(db, { nom: 'Alpha' });
		ajouterEntreprise(db, { nom: 'Rate 100% sûr' });
		ajouterEntreprise(db, { nom: 'snake_case' });
		ajouterEntreprise(db, { nom: 'snakeXcase' });
		expect(noms(listeEntreprises(db, { q: '%' }))).toEqual(['Rate 100% sûr']);
		expect(noms(listeEntreprises(db, { q: '_' }))).toEqual(['snake_case']);
		ajouterEntreprise(db, { nom: 'back\\slash' });
		expect(noms(listeEntreprises(db, { q: '\\' }))).toEqual(['back\\slash']);
	});

	it('une recherche et un statut se combinent', () => {
		expect(noms(listeEntreprises(jeu(), { q: 'a', statut: 'sans_suivi' }))).toEqual(['Delta']);
	});
});

describe('listeEntreprises : pages', () => {
	it('50 par page : 120 entreprises = 3 pages, la dernière en compte 20', () => {
		const db = ouverte();
		for (let i = 1; i <= 120; i++) ajouterEntreprise(db, { nom: `E${i}`, priorite: i });
		const p1 = listeEntreprises(db, { page: 1 });
		expect([p1.total, p1.pages, p1.page, p1.lignes.length]).toEqual([120, 3, 1, 50]);
		expect(p1.lignes[0].nom).toBe('E1');
		const p3 = listeEntreprises(db, { page: 3 });
		expect(p3.lignes.map((l) => l.nom)[0]).toBe('E101');
		expect(p3.lignes).toHaveLength(20);
	});

	it('une page hors limites est ramenée à la dernière, une page invalide à la première', () => {
		const db = ouverte();
		for (let i = 1; i <= 60; i++) ajouterEntreprise(db, { nom: `E${i}`, priorite: i });
		expect(listeEntreprises(db, { page: 99 }).page).toBe(2);
		expect(listeEntreprises(db, { page: 0 }).page).toBe(1);
		expect(listeEntreprises(db, { page: Number.NaN }).page).toBe(1);
	});

	it('aucune entreprise : une page vide', () => {
		const r = listeEntreprises(ouverte(), {});
		expect([r.total, r.pages, r.page, r.lignes]).toEqual([0, 1, 1, []]);
	});
});

describe('listeEntreprises : détails d’une ligne', () => {
	it('lien sûr, brouillons, dates et offres ouvertes du même SIRET', () => {
		const db = ouverte();
		const e = ajouterEntreprise(db, {
			nom: 'Beta',
			siret: '11111111100011',
			url_candidature: 'javascript:alert(1)',
			effectif: '10 à 19 salariés',
			origine: 'csv',
			priorite: 7,
			distance_km: 6.2
		});
		ajouterOffre(db, { titre: 'Offre Beta', siret: '11111111100011' });
		ajouterOffre(db, { titre: 'Offre voisine', entreprise: 'Beta', siret: null });
		changerStatut(db, { type: 'entreprise', id: e }, 'candidature_envoyee', T0);
		ajouterBrouillon(db, { type: 'entreprise', id: e }, 'spontanee', 'a');
		ajouterBrouillon(db, { type: 'entreprise', id: e }, 'lettre', 'b');
		const [ligne] = listeEntreprises(db, {}).lignes;
		expect(ligne).toMatchObject({
			id: e,
			effectif: '10 à 19 salariés',
			origine: 'csv',
			priorite: 7,
			distance_km: 6.2,
			lien: null,
			nbBrouillons: 2,
			contactee_le: '2026-11-18 09:00:00.000000'
		});
		expect(ligne.offresOuvertes.map((o) => o.titre)).toEqual(['Offre Beta']);
	});

	it('les brouillons d’une autre entreprise ne sont pas comptés', () => {
		const db = ouverte();
		const a = ajouterEntreprise(db, { nom: 'A', priorite: 1 });
		const b = ajouterEntreprise(db, { nom: 'B', priorite: 2 });
		for (const id of [a, b]) changerStatut(db, { type: 'entreprise', id }, 'interessante', T0);
		ajouterBrouillon(db, { type: 'entreprise', id: b }, 'spontanee', 'x');
		expect(listeEntreprises(db, {}).lignes.map((l) => l.nbBrouillons)).toEqual([0, 1]);
	});
});
