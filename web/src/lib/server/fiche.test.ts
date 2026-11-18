import { afterEach, describe, expect, it } from 'vitest';
import { creerBase } from './base-de-test.js';
import { ouvrir } from './db.js';
import { ajouterBrouillon, ajouterEntreprise, ajouterOffre, ajouterScore } from './donnees-de-test.js';
import { fiche } from './fiche.js';
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

describe('fiche d’une offre', () => {
	it('donne la carte et les brouillons rattachés, du plus ancien au plus récent', () => {
		const db = ouverte();
		const o = ajouterOffre(db, { titre: 'Dev', entreprise: 'ACME' });
		ajouterScore(db, o, 77);
		changerStatut(db, { type: 'offre', id: o }, 'interessante', T0);
		ajouterBrouillon(db, { type: 'offre', id: o }, 'lettre', 'Texte B', { cree_le: '2026-11-18 10:00:00.000000' });
		ajouterBrouillon(db, { type: 'offre', id: o }, 'email', 'Texte A', { gmail: true, cree_le: '2026-11-18 09:00:00.000000' });
		const f = fiche(db, 'offre', o);
		expect(f?.carte).toMatchObject({ genre: 'offre', titre: 'Dev', score: 77, statut: 'interessante' });
		expect(f?.brouillons.map((b) => [b.type, b.contenu, b.gmail_draft])).toEqual([
			['email', 'Texte A', true],
			['lettre', 'Texte B', false]
		]);
		expect(f?.offresOuvertes).toEqual([]);
	});

	it('une offre sans suivi : statut nul, aucun brouillon', () => {
		const db = ouverte();
		const o = ajouterOffre(db);
		expect(fiche(db, 'offre', o)).toMatchObject({ carte: { statut: null }, brouillons: [] });
	});

	it('ne reprend pas les brouillons d’une autre offre', () => {
		const db = ouverte();
		const a = ajouterOffre(db);
		const b = ajouterOffre(db);
		for (const id of [a, b]) changerStatut(db, { type: 'offre', id }, 'interessante', T0);
		ajouterBrouillon(db, { type: 'offre', id: b }, 'email', 'Autre');
		expect(fiche(db, 'offre', a)?.brouillons).toEqual([]);
	});
});

describe('fiche d’une entreprise', () => {
	it('donne ses brouillons, ses dates et les offres ouvertes du même SIRET', () => {
		const db = ouverte();
		const e = ajouterEntreprise(db, { nom: 'Beta', siret: '11111111100011' });
		ajouterOffre(db, { titre: 'Offre Beta', siret: '11111111100011' });
		ajouterOffre(db, { titre: 'Offre voisine', entreprise: 'Beta', siret: null });
		changerStatut(db, { type: 'entreprise', id: e }, 'candidature_envoyee', T0);
		ajouterBrouillon(db, { type: 'entreprise', id: e }, 'spontanee', 'Bonjour <script>alert(1)</script>');
		const f = fiche(db, 'entreprise', e);
		expect(f?.carte).toMatchObject({ genre: 'entreprise', titre: 'Beta', statut: 'candidature_envoyee' });
		expect(f?.brouillons.map((b) => [b.type, b.contenu])).toEqual([
			['spontanee', 'Bonjour <script>alert(1)</script>']
		]);
		expect(f?.offresOuvertes.map((o) => o.titre)).toEqual(['Offre Beta']);
		expect(f?.dates).toEqual({
			listee_le: null,
			contactee_le: '2026-11-18 09:00:00.000000',
			ignoree_le: null
		});
	});

	it('une offre n’a pas de dates d’entreprise', () => {
		const db = ouverte();
		const o = ajouterOffre(db);
		expect(fiche(db, 'offre', o)?.dates).toBeNull();
	});
});

it('renvoie null pour un identifiant inconnu', () => {
	const db = ouverte();
	expect(fiche(db, 'offre', 5)).toBeNull();
	expect(fiche(db, 'entreprise', 5)).toBeNull();
});
