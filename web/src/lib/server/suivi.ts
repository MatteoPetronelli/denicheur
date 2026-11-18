import type Database from 'better-sqlite3';
import { atteignables, estStatut, LIBELLES, type Statut } from '../statuts.js';

export class ErreurSuivi extends Error {}

export type Cible = { type: 'offre' | 'entreprise'; id: number };

/** Format de date écrit par SQLAlchemy : UTC sans fuseau, six décimales (le bot relit ce texte). */
export function dateBase(d: Date): string {
	return `${d.toISOString().replace('T', ' ').replace('Z', '')}000`;
}

const COLONNE = { offre: 'offre_id', entreprise: 'entreprise_id' } as const;
const TABLE = { offre: 'offres', entreprise: 'entreprises' } as const;
const INCONNUE = { offre: 'Offre introuvable.', entreprise: 'Entreprise introuvable.' } as const;
const DATE_DE_CONTACT: Partial<Record<Statut, string>> = { candidature_envoyee: 'contactee_le', ignoree: 'ignoree_le' };

/**
 * Fait avancer le suivi d'une offre ou d'une entreprise ; port de `repo._marquer` et `repo.marquer_entreprise`.
 * Renvoie « inchange » si le statut est déjà celui demandé.
 */
export function changerStatut(
	db: Database.Database,
	cible: Cible,
	statut: Statut,
	maintenant: Date
): 'change' | 'inchange' {
	if (!estStatut(statut)) throw new ErreurSuivi('Statut inconnu.');
	const colonne = COLONNE[cible.type];
	try {
		return db.transaction((): 'change' | 'inchange' => {
			if (!db.prepare(`select 1 from ${TABLE[cible.type]} where id = ?`).get(cible.id)) {
				throw new ErreurSuivi(INCONNUE[cible.type]);
			}
			const ligne = db.prepare(`select statut from candidatures where ${colonne} = ?`).get(cible.id) as
				| { statut: Statut }
				| undefined;
			const courant = ligne?.statut ?? null;
			if (courant === statut) return 'inchange';
			if (!atteignables(courant).includes(statut)) {
				throw new ErreurSuivi(
					`Transition impossible : ${courant ? LIBELLES[courant] : 'Nouvelle'} → ${LIBELLES[statut]}.`
				);
			}
			const t = dateBase(maintenant);
			const envoyee = statut === 'candidature_envoyee' ? t : null;
			if (courant === null) {
				db.prepare(
					`insert into candidatures (${colonne}, statut, envoyee_le, cree_le, maj_le) values (?, ?, ?, ?, ?)`
				).run(cible.id, statut, envoyee, t, t);
			} else {
				db.prepare(
					`update candidatures set statut = ?, maj_le = ?, envoyee_le = coalesce(?, envoyee_le) where ${colonne} = ?`
				).run(statut, t, envoyee, cible.id);
			}
			const date = DATE_DE_CONTACT[statut];
			if (cible.type === 'entreprise' && date) {
				db.prepare(`update entreprises set ${date} = ? where id = ?`).run(t, cible.id);
			}
			return 'change';
		}).immediate();
	} catch (e) {
		if ((e as { code?: string }).code === 'SQLITE_BUSY') throw new ErreurSuivi('Base occupée, réessaie.');
		throw e;
	}
}
