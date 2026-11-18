import { error } from '@sveltejs/kit';
import { base, ErreurBase } from '#lib/server/db.js';
import type { LayoutServerLoad } from './$types';

/** Sans base utilisable, aucune page ne s'affiche : message français et code 503. */
export const load: LayoutServerLoad = () => {
	try {
		base();
	} catch (e) {
		if (e instanceof ErreurBase) error(503, e.message);
		throw e;
	}
};
