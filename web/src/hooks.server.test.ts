import type { RequestEvent } from '@sveltejs/kit';
import { describe, expect, it } from 'vitest';
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
	const evenement = (hote: string) =>
		({ request: new Request('http://127.0.0.1/', { headers: { host: hote } }) }) as RequestEvent;
	const suite = async () => new Response('ok');

	it('laisse passer un hôte local', async () => {
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
});
