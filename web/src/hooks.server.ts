import type { Handle } from '@sveltejs/kit/hooks';

const HOTES = new Set(['127.0.0.1', 'localhost']);

/** Le tableau est local : tout autre en-tête `Host` (rebond DNS, port exposé par erreur) est refusé. */
export function hoteAutorise(hote: string | null): boolean {
	if (!hote) return false;
	return HOTES.has(hote.replace(/:\d{1,5}$/, ''));
}

export const handle: Handle = async ({ event, resolve }) => {
	const hote = event.request.headers.get('host');
	if (!hoteAutorise(hote)) {
		return new Response('Accès refusé : le tableau de bord est local.', { status: 403 });
	}
	// Une seule origine : SvelteKit refuse un formulaire dont l'en-tête Origin n'est pas celle du serveur.
	const origine = process.env.ORIGIN;
	if (origine && new URL(origine).host !== hote) {
		return new Response(null, { status: 308, headers: { location: `${origine}${event.url.pathname}${event.url.search}` } });
	}
	return resolve(event);
};
