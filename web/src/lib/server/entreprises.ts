import type Database from 'better-sqlite3';
import { lienSur } from '../liens.js';
import { borner, PAR_PAGE } from './pagination.js';
import type { Statut } from '../statuts.js';

export type OffreOuverte = { id: number; titre: string };

/** Offres retenues du même SIRET (comme le bot : jamais rapprochées par le nom), les plus récentes d'abord. */
export function offresOuvertesDuSiret(db: Database.Database, siret: string, limite = 3): OffreOuverte[] {
	return db
		.prepare('select id, titre from offres where siret = ? and motif_rejet is null order by id desc limit ?')
		.all(siret, limite) as OffreOuverte[];
}

export type FiltreEntreprises = { statut?: Statut | 'sans_suivi'; q?: string; page?: number };

export type LigneEntreprise = {
	id: number;
	nom: string;
	activite: string | null;
	commune: string | null;
	effectif: string | null;
	origine: string;
	priorite: number | null;
	distance_km: number | null;
	lien: string | null;
	statut: Statut | null;
	contactee_le: string | null;
	ignoree_le: string | null;
	nbBrouillons: number;
	offresOuvertes: OffreOuverte[];
};

export type ListeEntreprises = { lignes: LigneEntreprise[]; total: number; pages: number; page: number };

const JOINTURE = 'from entreprises e left join candidatures c on c.entreprise_id = e.id';

/** Les entreprises, filtrées côté SQL et paginées : la table en compte plus d'un millier. */
export function listeEntreprises(db: Database.Database, filtre: FiltreEntreprises): ListeEntreprises {
	const conditions: string[] = [];
	const valeurs: (string | number)[] = [];
	if (filtre.statut === 'sans_suivi') conditions.push('c.id is null');
	else if (filtre.statut) {
		conditions.push('c.statut = ?');
		valeurs.push(filtre.statut);
	}
	if (filtre.q) {
		conditions.push("e.nom like ? escape '\\'");
		valeurs.push(`%${filtre.q.replace(/[\\%_]/g, '\\$&')}%`);
	}
	const ou = conditions.length ? `where ${conditions.join(' and ')}` : '';
	const { n: total } = db.prepare(`select count(*) as n ${JOINTURE} ${ou}`).get(...valeurs) as { n: number };
	const { pages, page } = borner(total, filtre.page);
	const brutes = db
		.prepare(
			`select e.id, e.siret, e.nom, e.activite, e.commune, e.effectif, e.origine, e.priorite, e.distance_km,
			 e.url_candidature, c.statut, e.contactee_le, e.ignoree_le,
			 (select count(*) from brouillons b join candidatures cb on cb.id = b.candidature_id
			  where cb.entreprise_id = e.id) as nb_brouillons
			 ${JOINTURE} ${ou}
			 order by e.priorite is null, e.priorite, e.distance_km is null, e.distance_km, e.id
			 limit ? offset ?`
		)
		.all(...valeurs, PAR_PAGE, (page - 1) * PAR_PAGE) as (Omit<LigneEntreprise, 'lien' | 'nbBrouillons' | 'offresOuvertes'> & {
		siret: string;
		url_candidature: string | null;
		nb_brouillons: number;
	})[];
	const lignes = brutes.map(({ siret, url_candidature, nb_brouillons, ...reste }) => ({
		...reste,
		lien: lienSur(url_candidature),
		nbBrouillons: nb_brouillons,
		offresOuvertes: offresOuvertesDuSiret(db, siret)
	}));
	return { lignes, total, pages, page };
}
