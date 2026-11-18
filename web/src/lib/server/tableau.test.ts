import { afterEach, describe, expect, it } from 'vitest';
import { creerBase } from './base-de-test.js';
import { ouvrir } from './db.js';
import { ajouterEntreprise, ajouterOffre, ajouterScore } from './donnees-de-test.js';
import { changerStatut } from './suivi.js';
import { tableau } from './tableau.js';

const T0 = new Date('2026-11-18T09:00:00.000Z');
const T1 = new Date('2026-11-18T10:00:00.000Z');
const NOTIFIEE = '2026-11-18 08:00:00.000000';

const nettoyages: (() => void)[] = [];
afterEach(() => nettoyages.splice(0).reverse().forEach((f) => f()));

function ouverte() {
	const b = creerBase();
	nettoyages.push(b.nettoyer);
	const db = ouvrir(b.chemin);
	nettoyages.push(() => db.close());
	return db;
}

describe('colonnes', () => {
	it('range une offre et une entreprise de même statut dans la même colonne, avec leurs champs', () => {
		const db = ouverte();
		const o = ajouterOffre(db, { titre: 'Dev web', entreprise: 'ACME', distance_km: 12, url: 'https://x.test/o' });
		ajouterScore(db, o, 82);
		const e = ajouterEntreprise(db, {
			nom: 'Beta SA',
			activite: 'Programmation',
			commune: 'Marly',
			priorite: 3,
			distance_km: 4.5,
			url_candidature: 'https://beta.test/jobs'
		});
		changerStatut(db, { type: 'offre', id: o }, 'candidature_envoyee', T0);
		changerStatut(db, { type: 'entreprise', id: e }, 'candidature_envoyee', T1);
		const { colonnes } = tableau(db, {});
		expect(colonnes.candidature_envoyee.map((c) => [c.genre, c.titre])).toEqual([
			['entreprise', 'Beta SA'], // modifiée en dernier, donc en premier
			['offre', 'Dev web']
		]);
		expect(colonnes.candidature_envoyee[1]).toMatchObject({
			id: o,
			entreprise: 'ACME',
			score: 82,
			distance_km: 12,
			piste: 'alternance',
			lien: 'https://x.test/o',
			statut: 'candidature_envoyee'
		});
		expect(colonnes.candidature_envoyee[0]).toMatchObject({
			id: e,
			activite: 'Programmation',
			commune: 'Marly',
			priorite: 3,
			distance_km: 4.5,
			lien: 'https://beta.test/jobs',
			score: null
		});
		expect(colonnes.interessante).toEqual([]);
	});

	it('une offre sans score a un score nul, sans erreur', () => {
		const db = ouverte();
		const o = ajouterOffre(db);
		changerStatut(db, { type: 'offre', id: o }, 'interessante', T0);
		expect(tableau(db, {}).colonnes.interessante[0].score).toBeNull();
	});

	it('un lien qui ne commence pas par http n’est pas repris', () => {
		const db = ouverte();
		const e = ajouterEntreprise(db, { url_candidature: 'javascript:alert(1)' });
		const f = ajouterEntreprise(db, { url_candidature: 'ftp://x.test' });
		changerStatut(db, { type: 'entreprise', id: e }, 'interessante', T0);
		changerStatut(db, { type: 'entreprise', id: f }, 'interessante', T0);
		expect(tableau(db, {}).colonnes.interessante.map((c) => c.lien)).toEqual([null, null]);
	});
});

describe('nouvelles', () => {
	it('reprend les offres notifiées sans suivi, même quand une entreprise est suivie sans offre', () => {
		const db = ouverte();
		const e = ajouterEntreprise(db);
		changerStatut(db, { type: 'entreprise', id: e }, 'interessante', T0);
		const nouvelle = ajouterOffre(db, { titre: 'Nouvelle', notifiee_le: NOTIFIEE });
		const suivie = ajouterOffre(db, { titre: 'Suivie', notifiee_le: NOTIFIEE });
		ajouterOffre(db, { titre: 'Jamais notifiée' });
		changerStatut(db, { type: 'offre', id: suivie }, 'interessante', T0);
		const { nouvelles } = tableau(db, {});
		expect(nouvelles.map((c) => [c.id, c.titre, c.statut])).toEqual([[nouvelle, 'Nouvelle', null]]);
	});

	it('est limitée à 50 offres, les plus récemment notifiées d’abord', () => {
		const db = ouverte();
		for (let i = 0; i < 55; i++) {
			const minute = String(i).padStart(2, '0');
			ajouterOffre(db, { titre: `O${i}`, notifiee_le: `2026-11-18 08:${minute}:00.000000` });
		}
		const { nouvelles } = tableau(db, {});
		expect(nouvelles).toHaveLength(50);
		expect(nouvelles[0].titre).toBe('O54');
	});
});

describe('écartées', () => {
	it('sont comptées mais absentes des colonnes, listées seulement à la demande', () => {
		const db = ouverte();
		const o = ajouterOffre(db, { titre: 'Écartée' });
		changerStatut(db, { type: 'offre', id: o }, 'ignoree', T0);
		const sans = tableau(db, {});
		expect(sans.nbEcartees).toBe(1);
		expect(sans.ecartees).toEqual([]);
		expect(Object.values(sans.colonnes).flat()).toEqual([]);
		expect(tableau(db, { ecartees: true }).ecartees.map((c) => c.titre)).toEqual(['Écartée']);
	});
});

describe('filtres', () => {
	function base() {
		const db = ouverte();
		const s = ajouterOffre(db, { titre: 'Stage', piste: 'stage' });
		const a = ajouterOffre(db, { titre: 'Alternance', piste: 'alternance' });
		const x = ajouterOffre(db, { titre: 'Autre', piste: 'autre' });
		const e = ajouterEntreprise(db, { nom: 'Société' });
		for (const id of [s, a, x]) changerStatut(db, { type: 'offre', id }, 'interessante', T0);
		changerStatut(db, { type: 'entreprise', id: e }, 'interessante', T0);
		const titres = (f: Parameters<typeof tableau>[1]) => tableau(db, f).colonnes.interessante.map((c) => c.titre).sort();
		return titres;
	}

	it('sans filtre : tout', () => {
		expect(base()({})).toEqual(['Alternance', 'Autre', 'Société', 'Stage']);
	});

	it('stage : aucune entreprise', () => {
		expect(base()({ piste: 'stage' })).toEqual(['Stage']);
	});

	it('alternance : les offres d’alternance et les entreprises', () => {
		expect(base()({ piste: 'alternance' })).toEqual(['Alternance', 'Société']);
	});

	it('nature : offres seulement, ou entreprises seulement', () => {
		const titres = base();
		expect(titres({ nature: 'offre' })).toEqual(['Alternance', 'Autre', 'Stage']);
		expect(titres({ nature: 'entreprise' })).toEqual(['Société']);
	});

	it('les filtres s’appliquent aussi aux nouvelles et aux écartées', () => {
		const db = ouverte();
		ajouterOffre(db, { titre: 'N-stage', piste: 'stage', notifiee_le: NOTIFIEE });
		ajouterOffre(db, { titre: 'N-alt', piste: 'alternance', notifiee_le: NOTIFIEE });
		const e = ajouterEntreprise(db);
		changerStatut(db, { type: 'entreprise', id: e }, 'ignoree', T0);
		expect(tableau(db, { piste: 'stage' }).nouvelles.map((c) => c.titre)).toEqual(['N-stage']);
		expect(tableau(db, { nature: 'offre' }).nbEcartees).toBe(0);
		expect(tableau(db, { piste: 'stage' }).nbEcartees).toBe(0);
		expect(tableau(db, { nature: 'entreprise' }).nouvelles).toEqual([]);
		expect(tableau(db, { piste: 'alternance' }).nbEcartees).toBe(1);
	});
});
