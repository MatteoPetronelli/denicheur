import { estStatut, type Statut } from './statuts.js';

export type FiltresUrl = {
	piste: 'stage' | 'alternance' | undefined;
	nature: 'offre' | 'entreprise' | undefined;
	ecartees: boolean;
};

/** Filtres de l'adresse : toute valeur inconnue est ignorée. */
export function lireFiltres(params: URLSearchParams): FiltresUrl {
	const piste = params.get('piste');
	const nature = params.get('nature');
	return {
		piste: piste === 'stage' || piste === 'alternance' ? piste : undefined,
		nature: nature === 'offre' || nature === 'entreprise' ? nature : undefined,
		ecartees: params.get('ecartees') === '1'
	};
}

export type FiltresEntreprisesUrl = { statut: Statut | 'sans_suivi' | undefined; q: string | undefined; page: number };

export function lireFiltresEntreprises(params: URLSearchParams): FiltresEntreprisesUrl {
	const statut = params.get('statut');
	const page = Number(params.get('page') ?? 1);
	const q = (params.get('q') ?? '').trim().slice(0, 100);
	return {
		statut: statut === 'sans_suivi' || estStatut(statut) ? statut : undefined,
		q: q || undefined,
		page: Number.isInteger(page) && page >= 1 ? page : 1
	};
}

export type FiltresOffresUrl = {
	piste: 'stage' | 'alternance' | undefined;
	seuil: 'atteint' | 'sous' | undefined;
	page: number;
};

export function lireFiltresOffres(params: URLSearchParams): FiltresOffresUrl {
	const seuil = params.get('seuil');
	return {
		piste: lireFiltres(params).piste,
		seuil: seuil === 'atteint' || seuil === 'sous' ? seuil : undefined,
		page: lireFiltresEntreprises(params).page
	};
}
