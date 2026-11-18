import type { Handle } from '@sveltejs/kit/hooks';

const HOTES = new Set(['127.0.0.1', 'localhost']);

/** Le tableau est local : tout autre en-tête `Host` (rebond DNS, port exposé par erreur) est refusé. */
export function hoteAutorise(hote: string | null): boolean {
	if (!hote) return false;
	return HOTES.has(hote.replace(/:\d{1,5}$/, ''));
}

export const handle: Handle = async ({ event, resolve }) => {
	if (!hoteAutorise(event.request.headers.get('host'))) {
		return new Response('Accès refusé : le tableau de bord est local.', { status: 403 });
	}
	return resolve(event);
};
