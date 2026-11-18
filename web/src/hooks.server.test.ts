import type { RequestEvent } from '@sveltejs/kit';
import { afterEach, describe, expect, it } from 'vitest';
import { handle, hoteAutorise } from './hooks.server';

describe('hoteAutorise', () => {
	it.each(['127.0.0.1', '127.0.0.1:3000', 'localhost', 'localhost:5173'])('accepte %s', (hote) => {
		expect(hoteAutorise(hote)).toBe(true);
	});

	it.each([
		null,
		'',
		'exemple.fr',
		'exemple.fr:3000',
		'192.168.1.20:3000',
		'0.0.0.0',
		'localhost.exemple.fr',
		'localhost:3000:exemple',
		'localhost:port',
		'127.0.0.1.exemple.fr',
		'evil.com/127.0.0.1'
	])('refuse %s', (hote) => {
		expect(hoteAutorise(hote)).toBe(false);
	});
});

describe('handle', () => {
	const evenement = (hote: string, chemin = '/') =>
		({ request: new Request(`http://${hote}${chemin}`, { headers: { host: hote } }), url: new URL(`http://${hote}${chemin}`) }) as RequestEvent;
	const suite = async () => new Response('ok');
	const AVANT = process.env.ORIGIN;
	afterEach(() => {
		if (AVANT === undefined) delete process.env.ORIGIN;
		else process.env.ORIGIN = AVANT;
	});

	it('laisse passer un hôte local', async () => {
		delete process.env.ORIGIN;
		const reponse = await handle({ event: evenement('localhost:3000'), resolve: suite });
		expect(reponse.status).toBe(200);
	});

	it('répond 403 sans appeler la suite pour un autre hôte', async () => {
		let appelee = false;
		const reponse = await handle({
			event: evenement('exemple.fr'),
			resolve: async () => ((appelee = true), new Response('ok'))
		});
		expect(reponse.status).toBe(403);
		expect(appelee).toBe(false);
		expect(await reponse.text()).toContain('Accès refusé');
	});

	it('redirige localhost vers l’origine fixée, chemin et recherche conservés', async () => {
		process.env.ORIGIN = 'http://127.0.0.1:3000';
		const reponse = await handle({ event: evenement('localhost:3000', '/entreprises?q=a'), resolve: suite });
		expect(reponse.status).toBe(308);
		expect(reponse.headers.get('location')).toBe('http://127.0.0.1:3000/entreprises?q=a');
	});

	it('ne redirige pas quand l’hôte est déjà l’origine fixée', async () => {
		process.env.ORIGIN = 'http://127.0.0.1:3000';
		const reponse = await handle({ event: evenement('127.0.0.1:3000'), resolve: suite });
		expect(reponse.status).toBe(200);
	});

	it('un hôte étranger reste refusé même avec une origine fixée', async () => {
		process.env.ORIGIN = 'http://127.0.0.1:3000';
		const reponse = await handle({ event: evenement('exemple.fr:3000'), resolve: suite });
		expect(reponse.status).toBe(403);
	});
});
