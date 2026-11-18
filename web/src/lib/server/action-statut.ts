import { fail } from '@sveltejs/kit';
import type { Statut } from '../statuts.js';
import { base } from './db.js';
import { changerStatut, ErreurSuivi } from './suivi.js';

/** Traite le formulaire « changer le statut » commun au tableau et à la liste des entreprises. */
export async function traiterStatut(request: Request) {
	const form = await request.formData();
	const genre = form.get('genre');
	const id = Number(form.get('id'));
	const statut = form.get('statut');
	if ((genre !== 'offre' && genre !== 'entreprise') || !Number.isInteger(id) || id < 1) {
		return fail(400, { erreur: 'Demande invalide.', genre: null, id: null });
	}
	try {
		changerStatut(base(), { type: genre, id }, String(statut) as Statut, new Date()); // le statut est validé par changerStatut
	} catch (e) {
		if (e instanceof ErreurSuivi) return fail(400, { erreur: e.message, genre, id });
		throw e;
	}
	return { ok: true as const, genre, id };
}
