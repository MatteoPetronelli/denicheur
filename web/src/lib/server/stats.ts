import type Database from 'better-sqlite3';
import { LIBELLES, type Statut } from '../statuts.js';

const STATUTS = Object.keys(LIBELLES) as Statut[];
/** Une réponse d'un employeur : un entretien, une offre ou un refus. */
const REPONSES: Statut[] = ['entretien', 'offre', 'refus'];

export type Execution = {
	id: number;
	debut: string;
	mode: string;
	collectees: number;
	retenues: number;
	scorees: number;
	notifiees: number;
	duree_llm_s: number;
	nbErreurs: number;
};

export type Stats = {
	offres: { vues: number; retenues: number; notees: number; notifiees: number };
	candidatures: { offres: Record<Statut, number>; entreprises: Record<Statut, number> };
	reponses: { offres: number; entreprises: number; total: number };
	llm: { executions: number; moyenne_s: number; total_s: number };
	dernieres: Execution[];
};

const un = (db: Database.Database, sql: string): number => (db.prepare(sql).get() as { n: number }).n;

function parStatut(db: Database.Database, genre: 'offre_id' | 'entreprise_id'): Record<Statut, number> {
	const comptes = Object.fromEntries(STATUTS.map((s) => [s, 0])) as Record<Statut, number>;
	const lignes = db
		.prepare(`select statut, count(*) as n from candidatures where ${genre} is not null group by statut`)
		.all() as { statut: Statut; n: number }[];
	for (const { statut, n } of lignes) if (statut in comptes) comptes[statut] = n;
	return comptes;
}

/** Nombre d'erreurs d'une exécution ; leur texte n'est jamais lu ni affiché. */
function nombreDErreurs(brut: string): number {
	try {
		const valeur: unknown = JSON.parse(brut);
		return Array.isArray(valeur) ? valeur.length : 0;
	} catch {
		return 0;
	}
}

export function stats(db: Database.Database): Stats {
	const offres = {
		vues: un(db, 'select count(*) as n from offres'),
		retenues: un(db, 'select count(*) as n from offres where motif_rejet is null'),
		notees: un(db, 'select count(*) as n from scores'),
		notifiees: un(db, 'select count(*) as n from offres where notifiee_le is not null')
	};
	const candidatures = { offres: parStatut(db, 'offre_id'), entreprises: parStatut(db, 'entreprise_id') };
	const somme = (c: Record<Statut, number>) => REPONSES.reduce((total, s) => total + c[s], 0);
	const reponses = { offres: somme(candidatures.offres), entreprises: somme(candidatures.entreprises), total: 0 };
	reponses.total = reponses.offres + reponses.entreprises;
	const llm = db
		.prepare('select count(*) as executions, coalesce(avg(duree_llm_s), 0) as moyenne_s, coalesce(sum(duree_llm_s), 0) as total_s from executions')
		.get() as Stats['llm'];
	const dernieres = (
		db
			.prepare(
				`select id, debut, mode, offres_collectees as collectees, offres_retenues as retenues,
				 offres_scorees as scorees, offres_notifiees as notifiees, duree_llm_s, erreurs
				 from executions order by debut desc, id desc limit 10`
			)
			.all() as (Omit<Execution, 'nbErreurs'> & { erreurs: string })[]
	).map(({ erreurs, ...reste }) => ({ ...reste, nbErreurs: nombreDErreurs(erreurs) }));
	return { offres, candidatures, reponses, llm, dernieres };
}
