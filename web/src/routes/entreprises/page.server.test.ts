import { afterEach, beforeEach, expect, it } from 'vitest';
import { creerBase } from '#lib/server/base-de-test.js';
import { base, fermer } from '#lib/server/db.js';
import { ajouterEntreprise } from '#lib/server/donnees-de-test.js';
import { actions, load } from './+page.server';

const AVANT = process.env.DB_PATH;
let nettoyer = () => {};

beforeEach(() => {
	const b = creerBase();
	nettoyer = b.nettoyer;
	process.env.DB_PATH = b.chemin;
});
afterEach(() => {
	fermer();
	if (AVANT === undefined) delete process.env.DB_PATH;
	else process.env.DB_PATH = AVANT;
	nettoyer();
});

const charger = async (recherche: string) =>
	(await load({ url: new URL(`http://127.0.0.1/entreprises${recherche}`) } as Parameters<typeof load>[0])) as {
		filtres: { statut?: string; q?: string; page: number };
		liste: { lignes: { nom: string; statut: string | null }[]; total: number };
	};

function envoyer(champs: Record<string, string>) {
	const corps = new FormData();
	for (const [k, v] of Object.entries(champs)) corps.set(k, v);
	return actions.statut({ request: new Request('http://127.0.0.1/entreprises?/statut', { method: 'POST', body: corps }) } as Parameters<
		typeof actions.statut
	>[0]);
}

it('charge la liste filtrée par l’adresse', async () => {
	ajouterEntreprise(base(), { nom: 'Alpha', priorite: 1 });
	ajouterEntreprise(base(), { nom: 'Beta', priorite: 2 });
	const data = await charger('?q=alp&statut=sans_suivi');
	expect(data.filtres).toMatchObject({ q: 'alp', statut: 'sans_suivi', page: 1 });
	expect(data.liste.lignes.map((l) => l.nom)).toEqual(['Alpha']);
});

it('« Contactée » depuis la liste marque l’entreprise envoyée, avec sa date de contact', async () => {
	const e = ajouterEntreprise(base(), { nom: 'Alpha' });
	expect(await envoyer({ genre: 'entreprise', id: String(e), statut: 'candidature_envoyee' })).toMatchObject({ ok: true });
	const data = await charger('');
	expect(data.liste.lignes[0].statut).toBe('candidature_envoyee');
	const ligne = base().prepare('select contactee_le from entreprises where id = ?').get(e) as { contactee_le: string | null };
	expect(ligne.contactee_le).not.toBeNull();
});

it('« Écartée » puis une transition interdite : message français, rien ne change', async () => {
	const e = ajouterEntreprise(base(), { nom: 'Alpha' });
	await envoyer({ genre: 'entreprise', id: String(e), statut: 'ignoree' });
	const r = await envoyer({ genre: 'entreprise', id: String(e), statut: 'candidature_envoyee' });
	expect(r).toMatchObject({ status: 400, data: { erreur: expect.stringContaining('Transition impossible') } });
	expect((await charger('')).liste.lignes[0].statut).toBe('ignoree');
});
