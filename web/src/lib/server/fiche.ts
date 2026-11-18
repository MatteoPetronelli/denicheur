import type Database from 'better-sqlite3';
import { offresOuvertesDuSiret, type OffreOuverte } from './entreprises.js';
import { enCarte, type Carte, type Ligne } from './tableau.js';

export type Brouillon = { id: number; type: string; cree_le: string; gmail_draft: boolean; contenu: string };

export type Fiche = {
	carte: Carte;
	brouillons: Brouillon[];
	offresOuvertes: OffreOuverte[];
	dates: { listee_le: string | null; contactee_le: string | null; ignoree_le: string | null } | null;
};

const LIGNE_OFFRE = `select c.statut, null as entreprise_id, o.id as offre_id, o.titre, o.entreprise as o_entreprise,
	o.piste, o.distance_km as o_dist, o.url, s.score, null as nom, null as activite, null as commune,
	null as e_dist, null as priorite, null as url_candidature
	from offres o left join candidatures c on c.offre_id = o.id left join scores s on s.offre_id = o.id
	where o.id = ?`;

const LIGNE_ENTREPRISE = `select c.statut, e.id as entreprise_id, null as offre_id, null as titre, null as o_entreprise,
	null as piste, null as o_dist, null as url, null as score, e.nom, e.activite, e.commune,
	e.distance_km as e_dist, e.priorite, e.url_candidature
	from entreprises e left join candidatures c on c.entreprise_id = e.id
	where e.id = ?`;

/** Carte, brouillons rattachés (lecture seule) et, pour une entreprise, ses dates et ses offres ouvertes. */
export function fiche(db: Database.Database, genre: 'offre' | 'entreprise', id: number): Fiche | null {
	const ligne = db.prepare(genre === 'offre' ? LIGNE_OFFRE : LIGNE_ENTREPRISE).get(id) as Ligne | undefined;
	if (!ligne) return null;
	const colonne = genre === 'offre' ? 'offre_id' : 'entreprise_id';
	const brouillons = (
		db
			.prepare(
				`select b.id, b.type, b.cree_le, b.gmail_draft, b.contenu
				 from brouillons b join candidatures c on c.id = b.candidature_id
				 where c.${colonne} = ? order by b.cree_le, b.id`
			)
			.all(id) as (Omit<Brouillon, 'gmail_draft'> & { gmail_draft: number })[]
	).map((b) => ({ ...b, gmail_draft: b.gmail_draft === 1 }));
	if (genre === 'offre') return { carte: enCarte(ligne), brouillons, offresOuvertes: [], dates: null };
	const e = db.prepare('select siret, listee_le, contactee_le, ignoree_le from entreprises where id = ?').get(id) as {
		siret: string;
		listee_le: string | null;
		contactee_le: string | null;
		ignoree_le: string | null;
	};
	return {
		carte: enCarte(ligne),
		brouillons,
		offresOuvertes: offresOuvertesDuSiret(db, e.siret),
		dates: { listee_le: e.listee_le, contactee_le: e.contactee_le, ignoree_le: e.ignoree_le }
	};
}
