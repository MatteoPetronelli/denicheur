import { error } from '@sveltejs/kit';
import { lireFiltresOffres } from '#lib/filtres.js';
import { ErreurConfig, lireScoreMin } from '#lib/server/config.js';
import { base } from '#lib/server/db.js';
import { listeOffres } from '#lib/server/offres.js';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = ({ url }) => {
	const filtres = lireFiltresOffres(url.searchParams);
	let scoreMin: number;
	try {
		scoreMin = lireScoreMin();
	} catch (e) {
		if (e instanceof ErreurConfig) error(500, e.message);
		throw e;
	}
	return { filtres, scoreMin, liste: listeOffres(base(), scoreMin, filtres) };
};
