import { lireFiltres } from '#lib/filtres.js';
import { traiterStatut } from '#lib/server/action-statut.js';
import { base } from '#lib/server/db.js';
import { tableau } from '#lib/server/tableau.js';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = ({ url }) => {
	const filtres = lireFiltres(url.searchParams);
	return { filtres, tableau: tableau(base(), filtres) };
};

export const actions: Actions = { statut: ({ request }) => traiterStatut(request) };
