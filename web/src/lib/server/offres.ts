import type Database from 'better-sqlite3';
import { lienSur } from '../liens.js';
import type { Statut } from '../statuts.js';
import { borner, PAR_PAGE } from './pagination.js';
import type { Piste } from './tableau.js';

export type FiltreOffres = { piste?: 'stage' | 'alternance'; seuil?: 'atteint' | 'sous'; page?: number };

export type LigneOffre = {
	id: number;
	titre: string;
	entreprise: string | null;
	piste: Piste;
	score: number;
	distance_km: number | null;
	statut: Statut | null;
	sousSeuil: boolean;
	lien: string | null;
};

export type ListeOffres = { lignes: LigneOffre[]; total: number; pages: number; page: number };

/** Offres notées retenues par le préfiltre, avec celles sous le seuil de la configuration (`scoreMin`). */
export function listeOffres(db: Database.Database, scoreMin: number, filtre: FiltreOffres): ListeOffres {
	const conditions = ['o.motif_rejet is null'];
	const valeurs: (string | number)[] = [];
	if (filtre.piste) {
		conditions.push('o.piste = ?');
		valeurs.push(filtre.piste);
	}
	if (filtre.seuil) {
		conditions.push(filtre.seuil === 'sous' ? 's.score < ?' : 's.score >= ?');
		valeurs.push(scoreMin);
	}
	const ou = conditions.join(' and ');
	const depuis = 'from offres o join scores s on s.offre_id = o.id left join candidatures c on c.offre_id = o.id';
	const { n: total } = db.prepare(`select count(*) as n ${depuis} where ${ou}`).get(...valeurs) as { n: number };
	const { pages, page } = borner(total, filtre.page);
	const lignes = (
		db
			.prepare(
				`select o.id, o.titre, o.entreprise, o.piste, s.score, o.distance_km, c.statut, o.url
				 ${depuis} where ${ou}
				 order by s.score desc, o.id limit ? offset ?`
			)
			.all(...valeurs, PAR_PAGE, (page - 1) * PAR_PAGE) as (Omit<LigneOffre, 'sousSeuil' | 'lien'> & { url: string })[]
	).map(({ url, ...reste }) => ({ ...reste, sousSeuil: reste.score < scoreMin, lien: lienSur(url) }));
	return { lignes, total, pages, page };
}
