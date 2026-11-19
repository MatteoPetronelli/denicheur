import { expect, test } from 'vitest';
import { envoi } from './envoi.js';

function faux() {
	const attributs = new Map<string, string>();
	return {
		disabled: false,
		attributs,
		setAttribute: (n: string, v: string) => void attributs.set(n, v),
		removeAttribute: (n: string) => void attributs.delete(n)
	};
}

// Seuls `submitter` et `update` sont lus : le reste de l'objet SvelteKit n'est pas construit.
type Entree = Parameters<typeof envoi>[0];
type Suite = (o: { update: () => Promise<void> }) => Promise<void>;

test('le bouton est occupé et désactivé pendant l’envoi, puis libéré à la réponse', async () => {
	const bouton = faux();
	const suite = envoi({ submitter: bouton } as unknown as Entree) as unknown as Suite;
	expect(bouton.attributs.get('aria-busy')).toBe('true');
	expect(bouton.disabled).toBe(true);
	await suite({ update: async () => {} });
	expect(bouton.attributs.has('aria-busy')).toBe(false);
	expect(bouton.disabled).toBe(false);
});

test('le bouton est libéré même si la mise à jour échoue', async () => {
	const bouton = faux();
	const suite = envoi({ submitter: bouton } as unknown as Entree) as unknown as Suite;
	await expect(suite({ update: async () => Promise.reject(new Error('réseau')) })).rejects.toThrow('réseau');
	expect(bouton.attributs.has('aria-busy')).toBe(false);
	expect(bouton.disabled).toBe(false);
});

test('sans bouton envoyeur (touche Entrée dans un champ), rien ne casse', async () => {
	const suite = envoi({ submitter: null } as unknown as Entree) as unknown as Suite;
	await expect(suite({ update: async () => {} })).resolves.toBeUndefined();
});
