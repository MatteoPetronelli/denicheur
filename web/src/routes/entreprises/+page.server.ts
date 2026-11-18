import { lireFiltresEntreprises } from '#lib/filtres.js';
import { traiterStatut } from '#lib/server/action-statut.js';
import { base } from '#lib/server/db.js';
import { listeEntreprises } from '#lib/server/entreprises.js';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = ({ url }) => {
	const filtres = lireFiltresEntreprises(url.searchParams);
	return { filtres, liste: listeEntreprises(base(), filtres) };
};

export const actions: Actions = { statut: ({ request }) => traiterStatut(request) };
