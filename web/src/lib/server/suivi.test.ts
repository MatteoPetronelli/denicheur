import { execFileSync } from 'node:child_process';
import { resolve } from 'node:path';
import Database from 'better-sqlite3';
import { afterEach, describe, expect, it } from 'vitest';
import { creerBase } from './base-de-test.js';
import { ouvrir } from './db.js';
import { ajouterEntreprise, ajouterOffre } from './donnees-de-test.js';
import { changerStatut, ErreurSuivi } from './suivi.js';

const RACINE = resolve(import.meta.dirname, '../../../..');
const T0 = new Date('2026-11-18T09:30:15.123Z');
const T1 = new Date('2026-11-19T10:00:00.000Z');

const nettoyages: (() => void)[] = [];
afterEach(() => nettoyages.splice(0).reverse().forEach((f) => f()));

function ouverte() {
	const b = creerBase();
	nettoyages.push(b.nettoyer);
	const db = ouvrir(b.chemin);
	nettoyages.push(() => db.close());
	return { db, chemin: b.chemin };
}

const lignes = (db: Database.Database) => db.prepare('select * from candidatures').all() as Record<string, unknown>[];

/** Relit la ligne avec le code Python du bot. */
function relire(chemin: string, genre: 'offre' | 'entreprise', id: number) {
	const sortie = execFileSync('py', [resolve(RACINE, 'web/tests/relire.py'), chemin, genre, String(id)], {
		cwd: RACINE,
		encoding: 'utf-8'
	});
	return JSON.parse(sortie) as Record<string, string | null>;
}

describe('offre', () => {
	it('premier marquage : une ligne créée, envoyee_le posée pour « candidature envoyée »', () => {
		const { db, chemin } = ouverte();
		const id = ajouterOffre(db);
		expect(changerStatut(db, { type: 'offre', id }, 'candidature_envoyee', T0)).toBe('change');
		const [ligne] = lignes(db);
		expect(lignes(db)).toHaveLength(1);
		expect(ligne).toMatchObject({ offre_id: id, entreprise_id: null, statut: 'candidature_envoyee' });
		expect(ligne.envoyee_le).toBe('2026-11-18 09:30:15.123000');
		// lu par Python : même statut, dates valides
		expect(relire(chemin, 'offre', id)).toMatchObject({
			statut: 'candidature_envoyee',
			envoyee_le: '2026-11-18T09:30:15.123000'
		});
	});

	it('« intéressante » ne pose pas envoyee_le', () => {
		const { db } = ouverte();
		const id = ajouterOffre(db);
		changerStatut(db, { type: 'offre', id }, 'interessante', T0);
		expect(lignes(db)[0].envoyee_le).toBeNull();
	});

	it('une chaîne de transitions permises met à jour la même ligne', () => {
		const { db, chemin } = ouverte();
		const id = ajouterOffre(db);
		const cible = { type: 'offre', id } as const;
		changerStatut(db, cible, 'interessante', T0);
		changerStatut(db, cible, 'candidature_envoyee', T1);
		changerStatut(db, cible, 'relancee', T1);
		changerStatut(db, cible, 'entretien', T1);
		expect(lignes(db)).toHaveLength(1);
		expect(lignes(db)[0]).toMatchObject({ statut: 'entretien', envoyee_le: '2026-11-19 10:00:00.000000' });
		expect(relire(chemin, 'offre', id).statut).toBe('entretien');
	});

	it('transition refusée : erreur française et base inchangée', () => {
		const { db } = ouverte();
		const id = ajouterOffre(db);
		const cible = { type: 'offre', id } as const;
		changerStatut(db, cible, 'ignoree', T0);
		const avant = lignes(db);
		expect(() => changerStatut(db, cible, 'candidature_envoyee', T1)).toThrowError(ErreurSuivi);
		expect(() => changerStatut(db, cible, 'candidature_envoyee', T1)).toThrowError(/Écartée .* Candidature envoyée/);
		expect(lignes(db)).toEqual(avant);
	});

	it('nouvelle → relancée est refusé et ne crée aucune ligne', () => {
		const { db } = ouverte();
		const id = ajouterOffre(db);
		expect(() => changerStatut(db, { type: 'offre', id }, 'relancee', T0)).toThrowError(ErreurSuivi);
		expect(lignes(db)).toEqual([]);
	});

	it('« ignorée » est permise depuis un statut final', () => {
		const { db } = ouverte();
		const id = ajouterOffre(db);
		const cible = { type: 'offre', id } as const;
		changerStatut(db, cible, 'candidature_envoyee', T0);
		changerStatut(db, cible, 'refus', T0);
		expect(changerStatut(db, cible, 'ignoree', T1)).toBe('change');
	});

	it('même statut redemandé : rien ne change, envoyee_le d’origine conservée', () => {
		const { db } = ouverte();
		const id = ajouterOffre(db);
		const cible = { type: 'offre', id } as const;
		changerStatut(db, cible, 'candidature_envoyee', T0);
		expect(changerStatut(db, cible, 'candidature_envoyee', T1)).toBe('inchange');
		expect(lignes(db)[0]).toMatchObject({ envoyee_le: '2026-11-18 09:30:15.123000' });
	});

	it('offre inconnue ou statut inconnu : refusé sans rien écrire', () => {
		const { db } = ouverte();
		expect(() => changerStatut(db, { type: 'offre', id: 999 }, 'interessante', T0)).toThrowError(/Offre introuvable/);
		const id = ajouterOffre(db);
		expect(() => changerStatut(db, { type: 'offre', id }, 'nimporte' as never, T0)).toThrowError(/Statut inconnu/);
		expect(lignes(db)).toEqual([]);
	});
});

describe('entreprise', () => {
	it('« candidature envoyée » pose envoyee_le et contactee_le, ligne sans offre', () => {
		const { db, chemin } = ouverte();
		const id = ajouterEntreprise(db);
		changerStatut(db, { type: 'entreprise', id }, 'candidature_envoyee', T0);
		expect(lignes(db)[0]).toMatchObject({ offre_id: null, entreprise_id: id, statut: 'candidature_envoyee' });
		const relu = relire(chemin, 'entreprise', id);
		expect(relu).toMatchObject({
			statut: 'candidature_envoyee',
			envoyee_le: '2026-11-18T09:30:15.123000',
			contactee_le: '2026-11-18T09:30:15.123000',
			ignoree_le: null
		});
	});

	it('« ignorée » pose ignoree_le seulement', () => {
		const { db, chemin } = ouverte();
		const id = ajouterEntreprise(db);
		changerStatut(db, { type: 'entreprise', id }, 'ignoree', T0);
		expect(relire(chemin, 'entreprise', id)).toMatchObject({
			statut: 'ignoree',
			contactee_le: null,
			ignoree_le: '2026-11-18T09:30:15.123000'
		});
	});

	it('« intéressante » ne pose aucune date de contact ni d’écart', () => {
		const { db, chemin } = ouverte();
		const id = ajouterEntreprise(db);
		changerStatut(db, { type: 'entreprise', id }, 'interessante', T0);
		expect(relire(chemin, 'entreprise', id)).toMatchObject({ contactee_le: null, ignoree_le: null });
	});

	it('même statut redemandé : dates d’origine conservées', () => {
		const { db, chemin } = ouverte();
		const id = ajouterEntreprise(db);
		const cible = { type: 'entreprise', id } as const;
		changerStatut(db, cible, 'candidature_envoyee', T0);
		expect(changerStatut(db, cible, 'candidature_envoyee', T1)).toBe('inchange');
		expect(relire(chemin, 'entreprise', id).contactee_le).toBe('2026-11-18T09:30:15.123000');
	});

	it('entreprise inconnue refusée sans ligne ; une entreprise contactée ne revient pas à « intéressante »', () => {
		const { db } = ouverte();
		expect(() => changerStatut(db, { type: 'entreprise', id: 42 }, 'interessante', T0)).toThrowError(
			/Entreprise introuvable/
		);
		const id = ajouterEntreprise(db);
		const cible = { type: 'entreprise', id } as const;
		changerStatut(db, cible, 'candidature_envoyee', T0);
		expect(() => changerStatut(db, cible, 'interessante', T1)).toThrowError(ErreurSuivi);
		expect(lignes(db)).toHaveLength(1);
	});

	it('une offre et une entreprise de même identifiant ont chacune leur ligne', () => {
		const { db } = ouverte();
		const o = ajouterOffre(db);
		const e = ajouterEntreprise(db);
		changerStatut(db, { type: 'offre', id: o }, 'interessante', T0);
		changerStatut(db, { type: 'entreprise', id: e }, 'candidature_envoyee', T0);
		expect(lignes(db)).toHaveLength(2);
	});
});

describe('base occupée', () => {
	it('un verrou d’un autre processus donne « Base occupée » et le statut reste inchangé', () => {
		const { db, chemin } = ouverte();
		const id = ajouterOffre(db);
		db.pragma('busy_timeout = 50');
		const autre = new Database(chemin);
		nettoyages.push(() => autre.close());
		autre.exec('begin immediate');
		expect(() => changerStatut(db, { type: 'offre', id }, 'interessante', T0)).toThrowError(/Base occupée/);
		autre.exec('rollback');
		expect(lignes(db)).toEqual([]);
	});

	it('le verrou d’écriture est pris dès le début : la lecture et l’écriture voient le même état', () => {
		const { db, chemin } = ouverte();
		db.pragma('busy_timeout = 50');
		const autre = new Database(chemin);
		nettoyages.push(() => autre.close());
		autre.exec('begin immediate');
		// Une transaction différée lirait d’abord et répondrait « introuvable » ; la nôtre attend le verrou.
		expect(() => changerStatut(db, { type: 'offre', id: 999 }, 'interessante', T0)).toThrowError(/Base occupée/);
		autre.exec('rollback');
	});
});
