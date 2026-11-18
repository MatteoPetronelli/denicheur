import { afterEach, describe, expect, it } from 'vitest';
import { creerBase } from './base-de-test.js';
import { ouvrir } from './db.js';
import { ajouterEntreprise, ajouterExecution, ajouterOffre, ajouterScore } from './donnees-de-test.js';
import { formaterDuree } from '../duree.js';
import { stats } from './stats.js';
import { changerStatut } from './suivi.js';

const T0 = new Date('2026-11-18T09:00:00.000Z');
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

describe('stats : offres', () => {
	it('10 offres dont 4 rejetées, 5 notées : 10 vues, 6 retenues, 5 notées', () => {
		const db = ouverte();
		const ids = Array.from({ length: 10 }, (_, i) => ajouterOffre(db, { motif_rejet: i < 4 ? 'niveau' : null }));
		for (const id of ids.slice(4, 9)) ajouterScore(db, id, 70);
		ajouterOffre(db, { notifiee_le: NOTIFIEE }); // 11e, notifiée
		const s = stats(db);
		expect(s.offres).toEqual({ vues: 11, retenues: 7, notees: 5, notifiees: 1 });
	});

	it('une base vide donne des zéros, sans erreur', () => {
		const s = stats(ouverte());
		expect(s.offres).toEqual({ vues: 0, retenues: 0, notees: 0, notifiees: 0 });
		expect(s.reponses).toEqual({ offres: 0, entreprises: 0, total: 0 });
		expect(s.llm).toEqual({ executions: 0, moyenne_s: 0, total_s: 0 });
		expect(s.dernieres).toEqual([]);
		expect(Object.values(s.candidatures.offres).every((n) => n === 0)).toBe(true);
	});
});

describe('stats : candidatures et réponses', () => {
	it('sépare les candidatures d’offres et d’entreprises, statut par statut', () => {
		const db = ouverte();
		const o = [ajouterOffre(db), ajouterOffre(db), ajouterOffre(db)];
		const e = [ajouterEntreprise(db), ajouterEntreprise(db), ajouterEntreprise(db)];
		for (const id of o.slice(0, 2)) changerStatut(db, { type: 'offre', id }, 'candidature_envoyee', T0);
		changerStatut(db, { type: 'offre', id: o[2] }, 'ignoree', T0);
		for (const id of e) changerStatut(db, { type: 'entreprise', id }, 'candidature_envoyee', T0);
		const s = stats(db);
		expect(s.candidatures.offres.candidature_envoyee).toBe(2);
		expect(s.candidatures.offres.ignoree).toBe(1);
		expect(s.candidatures.entreprises.candidature_envoyee).toBe(3);
		expect(s.candidatures.entreprises.ignoree).toBe(0);
	});

	it('2 envoyées et 1 refus : 1 réponse', () => {
		const db = ouverte();
		const [a, b, c] = [ajouterOffre(db), ajouterOffre(db), ajouterOffre(db)];
		for (const id of [a, b, c]) changerStatut(db, { type: 'offre', id }, 'candidature_envoyee', T0);
		changerStatut(db, { type: 'offre', id: c }, 'refus', T0);
		const s = stats(db);
		expect(s.candidatures.offres.candidature_envoyee).toBe(2);
		expect(s.reponses).toEqual({ offres: 1, entreprises: 0, total: 1 });
	});

	it('une réponse est un entretien, une offre ou un refus, pour les offres comme pour les entreprises', () => {
		const db = ouverte();
		const finaux = ['entretien', 'offre', 'refus', 'sans_reponse', 'relancee'] as const;
		const offres = finaux.map(() => ajouterOffre(db));
		const entreprises = finaux.map(() => ajouterEntreprise(db));
		finaux.forEach((statut, i) => {
			changerStatut(db, { type: 'offre', id: offres[i] }, 'candidature_envoyee', T0);
			changerStatut(db, { type: 'offre', id: offres[i] }, statut, T0);
			changerStatut(db, { type: 'entreprise', id: entreprises[i] }, 'candidature_envoyee', T0);
			changerStatut(db, { type: 'entreprise', id: entreprises[i] }, statut, T0);
		});
		expect(stats(db).reponses).toEqual({ offres: 3, entreprises: 3, total: 6 });
	});
});

describe('stats : LLM et exécutions', () => {
	it('durée moyenne et totale tirées des exécutions', () => {
		const db = ouverte();
		ajouterExecution(db, { duree_llm_s: 60 });
		ajouterExecution(db, { duree_llm_s: 120 });
		ajouterExecution(db, { duree_llm_s: 0 });
		expect(stats(db).llm).toEqual({ executions: 3, moyenne_s: 60, total_s: 180 });
	});

	it('liste les dix dernières exécutions, la plus récente d’abord, avec le nombre d’erreurs seulement', () => {
		const db = ouverte();
		for (let i = 1; i <= 12; i++) {
			const jour = String(i).padStart(2, '0');
			ajouterExecution(db, {
				debut: `2026-11-${jour} 08:30:00.000000`,
				mode: i === 12 ? 'stage' : 'auto',
				collectees: i,
				retenues: i + 1,
				scorees: i + 2,
				notifiees: i + 3,
				duree_llm_s: i * 10,
				erreurs: i === 12 ? ['source lba : HTTPError', 'clé secrète abc123'] : []
			});
		}
		const { dernieres } = stats(db);
		expect(dernieres).toHaveLength(10);
		expect(dernieres[0]).toEqual({
			id: 12,
			debut: '2026-11-12 08:30:00.000000',
			mode: 'stage',
			collectees: 12,
			retenues: 13,
			scorees: 14,
			notifiees: 15,
			duree_llm_s: 120,
			nbErreurs: 2
		});
		expect(dernieres[9].id).toBe(3);
		expect(JSON.stringify(dernieres)).not.toContain('abc123');
		expect(JSON.stringify(dernieres)).not.toContain('HTTPError');
	});

	it('des erreurs absentes ou illisibles comptent zéro', () => {
		const db = ouverte();
		ajouterExecution(db);
		db.prepare("insert into executions (debut, mode, offres_collectees, offres_retenues, offres_scorees, offres_notifiees, erreurs, duree_llm_s) values ('2026-11-19 08:00:00.000000', 'auto', 0, 0, 0, 0, 'pas du json', 0)").run();
		expect(stats(db).dernieres.map((d) => d.nbErreurs)).toEqual([0, 0]);
	});
});

describe('formaterDuree', () => {
	it.each([
		[0, '0 s'],
		[4.4, '4 s'],
		[59.6, '1 min'],
		[60, '1 min'],
		[75, '1 min 15 s'],
		[3600, '60 min'],
		[3725, '62 min 5 s']
	])('%s s → %s', (secondes, attendu) => {
		expect(formaterDuree(secondes)).toBe(attendu);
	});
});
