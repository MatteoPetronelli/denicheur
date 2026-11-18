import type Database from 'better-sqlite3';
import { lienSur } from '../liens.js';
import { COLONNES, type Statut } from '../statuts.js';

export type Piste = 'stage' | 'alternance' | 'autre';

export type Carte = {
	genre: 'offre' | 'entreprise';
	id: number;
	statut: Statut | null;
	titre: string;
	entreprise: string | null;
	activite: string | null;
	commune: string | null;
	score: number | null;
	distance_km: number | null;
	piste: Piste | null;
	priorite: number | null;
	lien: string | null;
};

export type Filtres = { piste?: 'stage' | 'alternance'; nature?: 'offre' | 'entreprise'; ecartees?: boolean };

export type Tableau = {
	colonnes: Record<string, Carte[]>;
	nouvelles: Carte[];
	ecartees: Carte[];
	nbEcartees: number;
};

export type Ligne = {
	statut: Statut | null;
	offre_id: number | null;
	entreprise_id: number | null;
	titre: string | null;
	o_entreprise: string | null;
	piste: Piste | null;
	o_dist: number | null;
	url: string | null;
	score: number | null;
	nom: string | null;
	activite: string | null;
	commune: string | null;
	e_dist: number | null;
	priorite: number | null;
	url_candidature: string | null;
};

const CHAMPS_OFFRE = `o.id as offre_id, o.titre, o.entreprise as o_entreprise, o.piste, o.distance_km as o_dist,
	o.url, s.score`;

export function enCarte(l: Ligne): Carte {
	if (l.offre_id !== null) {
		return {
			genre: 'offre',
			id: l.offre_id,
			statut: l.statut,
			titre: l.titre ?? '',
			entreprise: l.o_entreprise,
			activite: null,
			commune: null,
			score: l.score,
			distance_km: l.o_dist,
			piste: l.piste,
			priorite: null,
			lien: lienSur(l.url)
		};
	}
	return {
		genre: 'entreprise',
		id: l.entreprise_id ?? 0,
		statut: l.statut,
		titre: l.nom ?? '',
		entreprise: null,
		activite: l.activite,
		commune: l.commune,
		score: null,
		distance_km: l.e_dist,
		piste: null,
		priorite: l.priorite,
		lien: lienSur(l.url_candidature)
	};
}

/** Les entreprises n'ont pas de piste : elles comptent comme alternance. */
function garde(c: Carte, f: Filtres): boolean {
	if (f.nature && c.genre !== f.nature) return false;
	if (f.piste && (c.genre === 'entreprise' ? f.piste !== 'alternance' : c.piste !== f.piste)) return false;
	return true;
}

export function tableau(db: Database.Database, filtres: Filtres): Tableau {
	const suivies = (
		db
			.prepare(
				`select c.statut, c.entreprise_id, ${CHAMPS_OFFRE},
				 e.nom, e.activite, e.commune, e.distance_km as e_dist, e.priorite, e.url_candidature
				 from candidatures c
				 left join offres o on o.id = c.offre_id
				 left join scores s on s.offre_id = o.id
				 left join entreprises e on e.id = c.entreprise_id
				 order by c.maj_le desc, c.id desc`
			)
			.all() as Ligne[]
	)
		.map(enCarte)
		.filter((c) => garde(c, filtres));

	const colonnes: Record<string, Carte[]> = Object.fromEntries(COLONNES.map((s) => [s, []]));
	const ecartees: Carte[] = [];
	for (const c of suivies) {
		if (c.statut === 'ignoree') ecartees.push(c);
		else if (c.statut) colonnes[c.statut]?.push(c);
	}

	// `offre_id IS NOT NULL` : un suivi d'entreprise a offre_id NULL, et NOT IN avec NULL ne renvoie rien.
	const nouvelles =
		filtres.nature === 'entreprise'
			? []
			: (
					db
						.prepare(
							`select null as statut, null as entreprise_id, ${CHAMPS_OFFRE}
							 from offres o left join scores s on s.offre_id = o.id
							 where o.notifiee_le is not null
							   and o.id not in (select offre_id from candidatures where offre_id is not null)
							 order by o.notifiee_le desc, o.id desc`
						)
						.all() as Ligne[]
				)
					.map(enCarte)
					.filter((c) => garde(c, filtres))
					.slice(0, 50);

	return {
		colonnes,
		nouvelles,
		ecartees: filtres.ecartees ? ecartees : [],
		nbEcartees: ecartees.length
	};
}
