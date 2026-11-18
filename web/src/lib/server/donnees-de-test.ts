// Jeux de données de test : insertions SQL brutes, car les valeurs par défaut du schéma sont posées par Python.
import type Database from 'better-sqlite3';

const MAINTENANT = '2026-11-18 09:00:00.000000';

export type OffreTest = {
	titre?: string;
	entreprise?: string | null;
	siret?: string | null;
	piste?: 'stage' | 'alternance' | 'autre';
	distance_km?: number | null;
	motif_rejet?: string | null;
	notifiee_le?: string | null;
	vue_le?: string;
	url?: string;
};

let compteur = 0;

export function ajouterOffre(db: Database.Database, o: OffreTest = {}): number {
	compteur += 1;
	const r = db
		.prepare(
			`insert into offres (source, source_id, url, cle_dedup, titre, entreprise, siret, distance_km, lieu_a_verifier,
			 piste, debut_des_que_possible, description, motif_rejet, vue_le, notifiee_le)
			 values ('test', ?, ?, ?, ?, ?, ?, ?, 0, ?, 0, 'Description', ?, ?, ?)`
		)
		.run(
			String(compteur),
			o.url ?? `https://exemple.test/offre/${compteur}`,
			`cle${compteur}`,
			o.titre ?? `Développeur ${compteur}`,
			o.entreprise === undefined ? `Société ${compteur}` : o.entreprise,
			o.siret ?? null,
			o.distance_km ?? null,
			o.piste ?? 'alternance',
			o.motif_rejet ?? null,
			o.vue_le ?? MAINTENANT,
			o.notifiee_le ?? null
		);
	return Number(r.lastInsertRowid);
}

export function ajouterScore(db: Database.Database, offreId: number, score: number, piste = 'alternance'): void {
	db.prepare(
		`insert into scores (offre_id, piste, score, points_forts, points_faibles, projet_a_citer, resume, modele,
		 prompt_tokens, output_tokens, duree_s, cree_le)
		 values (?, ?, ?, '[]', '[]', 'Projet', 'Résumé', 'test', 1, 1, 1.0, ?)`
	).run(offreId, piste, score, MAINTENANT);
}

export type EntrepriseTest = {
	nom?: string;
	siret?: string;
	activite?: string | null;
	commune?: string | null;
	priorite?: number | null;
	distance_km?: number | null;
	url_candidature?: string | null;
	origine?: 'csv' | 'lba' | 'sirene';
	effectif?: string | null;
};

export function ajouterEntreprise(db: Database.Database, e: EntrepriseTest = {}): number {
	compteur += 1;
	const r = db
		.prepare(
			`insert into entreprises (siret, nom, activite, commune, priorite, distance_km, url_candidature, origine,
			 effectif, cree_le, maj_le) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
		)
		.run(
			e.siret ?? String(compteur).padStart(14, '0'),
			e.nom ?? `Entreprise ${compteur}`,
			e.activite ?? null,
			e.commune ?? null,
			e.priorite ?? null,
			e.distance_km ?? null,
			e.url_candidature ?? null,
			e.origine ?? 'sirene',
			e.effectif ?? null,
			MAINTENANT,
			MAINTENANT
		);
	return Number(r.lastInsertRowid);
}

export function ajouterBrouillon(
	db: Database.Database,
	cible: { type: 'offre' | 'entreprise'; id: number },
	type: string,
	contenu: string,
	options: { gmail?: boolean; cree_le?: string } = {}
): number {
	const colonne = cible.type === 'offre' ? 'offre_id' : 'entreprise_id';
	const ligne = db.prepare(`select id from candidatures where ${colonne} = ?`).get(cible.id) as { id: number };
	const r = db
		.prepare('insert into brouillons (candidature_id, type, contenu, gmail_draft, cree_le) values (?, ?, ?, ?, ?)')
		.run(ligne.id, type, contenu, options.gmail ? 1 : 0, options.cree_le ?? MAINTENANT);
	return Number(r.lastInsertRowid);
}

export type ExecutionTest = {
	debut?: string;
	mode?: string;
	collectees?: number;
	retenues?: number;
	scorees?: number;
	notifiees?: number;
	erreurs?: unknown;
	duree_llm_s?: number;
};

export function ajouterExecution(db: Database.Database, e: ExecutionTest = {}): number {
	const r = db
		.prepare(
			`insert into executions (debut, mode, offres_collectees, offres_retenues, offres_scorees, offres_notifiees,
			 erreurs, duree_llm_s) values (?, ?, ?, ?, ?, ?, ?, ?)`
		)
		.run(
			e.debut ?? MAINTENANT,
			e.mode ?? 'auto',
			e.collectees ?? 0,
			e.retenues ?? 0,
			e.scorees ?? 0,
			e.notifiees ?? 0,
			JSON.stringify(e.erreurs ?? []),
			e.duree_llm_s ?? 0
		);
	return Number(r.lastInsertRowid);
}
