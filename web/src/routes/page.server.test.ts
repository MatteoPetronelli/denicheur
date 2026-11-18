import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { creerBase } from '#lib/server/base-de-test.js';
import { fermer, base } from '#lib/server/db.js';
import { ajouterEntreprise, ajouterOffre } from '#lib/server/donnees-de-test.js';
import type { FiltresUrl } from '#lib/filtres.js';
import type { Tableau } from '#lib/server/tableau.js';
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

const charger = async (recherche = '') =>
	(await load({ url: new URL(`http://127.0.0.1/${recherche}`) } as Parameters<typeof load>[0])) as {
		filtres: FiltresUrl;
		tableau: Tableau;
	};

function envoyer(champs: Record<string, string>) {
	const corps = new FormData();
	for (const [k, v] of Object.entries(champs)) corps.set(k, v);
	return actions.statut({
		request: new Request('http://127.0.0.1/?/statut', { method: 'POST', body: corps })
	} as Parameters<typeof actions.statut>[0]);
}

const statutEnBase = (genre: 'offre' | 'entreprise', id: number) =>
	base()
		.prepare(`select statut from candidatures where ${genre}_id = ?`)
		.get(id) as { statut: string } | undefined;

describe('chargement', () => {
	it('lit les filtres dans l’adresse et les renvoie à la page', async () => {
		const data = await charger('?piste=stage&nature=offre&ecartees=1');
		expect(data.filtres).toEqual({ piste: 'stage', nature: 'offre', ecartees: true });
	});

	it('ignore une valeur de filtre inconnue', async () => {
		const data = await charger('?piste=nimporte&nature=quoi&ecartees=oui');
		expect(data.filtres).toEqual({ piste: undefined, nature: undefined, ecartees: false });
	});

	it('renvoie les colonnes du tableau', async () => {
		const o = ajouterOffre(base(), { titre: 'Dev' });
		await envoyer({ genre: 'offre', id: String(o), statut: 'interessante' });
		const data = await charger();
		expect(data.tableau.colonnes.interessante.map((c) => c.titre)).toEqual(['Dev']);
	});
});

describe('action « statut »', () => {
	it('change le statut d’une offre', async () => {
		const o = ajouterOffre(base());
		const r = await envoyer({ genre: 'offre', id: String(o), statut: 'candidature_envoyee' });
		expect(r).toMatchObject({ ok: true });
		expect(statutEnBase('offre', o)?.statut).toBe('candidature_envoyee');
	});

	it('change le statut d’une entreprise et pose sa date de contact', async () => {
		const e = ajouterEntreprise(base());
		await envoyer({ genre: 'entreprise', id: String(e), statut: 'candidature_envoyee' });
		expect(statutEnBase('entreprise', e)?.statut).toBe('candidature_envoyee');
		const ligne = base().prepare('select contactee_le from entreprises where id = ?').get(e) as {
			contactee_le: string | null;
		};
		expect(ligne.contactee_le).not.toBeNull();
	});

	it('refuse une transition interdite avec un message français, base inchangée', async () => {
		const o = ajouterOffre(base());
		await envoyer({ genre: 'offre', id: String(o), statut: 'ignoree' });
		const r = await envoyer({ genre: 'offre', id: String(o), statut: 'candidature_envoyee' });
		expect(r).toMatchObject({ status: 400, data: { erreur: expect.stringContaining('Transition impossible'), genre: 'offre', id: o } });
		expect(statutEnBase('offre', o)?.statut).toBe('ignoree');
	});

	it.each([
		{ genre: 'autre', id: '1', statut: 'interessante' },
		{ genre: 'offre', id: 'abc', statut: 'interessante' },
		{ genre: 'offre', id: '1.5', statut: 'interessante' },
		{ genre: 'offre', id: '0', statut: 'interessante' },
		{ genre: 'offre', id: '-3', statut: 'interessante' },
		{ id: '1', statut: 'interessante' }
	])('refuse une demande invalide %j sans rien écrire', async (champs) => {
		ajouterOffre(base());
		const r = await envoyer(champs as Record<string, string>);
		expect(r).toMatchObject({ status: 400, data: { erreur: 'Demande invalide.' } });
		expect(base().prepare('select count(*) as n from candidatures').get()).toEqual({ n: 0 });
	});

	it.each([{ genre: 'offre', id: '1', statut: 'nimporte' }, { genre: 'offre', id: '1' }])(
		'refuse un statut absent ou inconnu %j sans rien écrire',
		async (champs) => {
			ajouterOffre(base());
			const r = await envoyer(champs as Record<string, string>);
			expect(r).toMatchObject({ status: 400, data: { erreur: 'Statut inconnu.' } });
			expect(base().prepare('select count(*) as n from candidatures').get()).toEqual({ n: 0 });
		}
	);

	it('une offre ou une entreprise inconnue est refusée', async () => {
		const r = await envoyer({ genre: 'entreprise', id: '999', statut: 'interessante' });
		expect(r).toMatchObject({ status: 400, data: { erreur: 'Entreprise introuvable.' } });
	});
});
