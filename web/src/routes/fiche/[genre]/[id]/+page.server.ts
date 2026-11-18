import { error } from '@sveltejs/kit';
import { base } from '#lib/server/db.js';
import { fiche } from '#lib/server/fiche.js';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = ({ params }) => {
	if (params.genre !== 'offre' && params.genre !== 'entreprise') error(404, 'Fiche introuvable.');
	const f = fiche(base(), params.genre, Number(params.id)); // un identifiant illisible ne correspond à aucune ligne
	if (!f) error(404, 'Fiche introuvable.');
	return f;
};
