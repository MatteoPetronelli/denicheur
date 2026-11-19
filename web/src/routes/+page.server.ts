import { error } from '@sveltejs/kit';
import { lireFiltres } from '#lib/filtres.js';
import { traiterStatut } from '#lib/server/action-statut.js';
import { ErreurConfig, lireScoreMin } from '#lib/server/config.js';
import { base } from '#lib/server/db.js';
import { tableau } from '#lib/server/tableau.js';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = ({ url }) => {
	const filtres = lireFiltres(url.searchParams);
	let scoreMin: number;
	try {
		scoreMin = lireScoreMin(); // niveau du score sur les cartes
	} catch (e) {
		if (e instanceof ErreurConfig) error(500, e.message);
		throw e;
	}
	return { filtres, scoreMin, tableau: tableau(base(), filtres) };
};

export const actions: Actions = { statut: ({ request }) => traiterStatut(request) };
