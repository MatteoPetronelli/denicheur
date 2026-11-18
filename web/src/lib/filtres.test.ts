import { describe, expect, it } from 'vitest';
import { lireFiltres, lireFiltresEntreprises, lireFiltresOffres } from './filtres.js';

const params = (recherche: string) => new URLSearchParams(recherche);

describe('lireFiltres', () => {
	it('lit piste, nature et écartées', () => {
		expect(lireFiltres(params('piste=stage&nature=offre&ecartees=1'))).toEqual({
			piste: 'stage',
			nature: 'offre',
			ecartees: true
		});
	});
	it('ignore les valeurs inconnues', () => {
		expect(lireFiltres(params('piste=x&nature=y&ecartees=oui'))).toEqual({
			piste: undefined,
			nature: undefined,
			ecartees: false
		});
	});
});

describe('lireFiltresEntreprises', () => {
	it('lit statut, recherche et page', () => {
		expect(lireFiltresEntreprises(params('statut=sans_suivi&q=%20alpha%20&page=3'))).toEqual({
			statut: 'sans_suivi',
			q: 'alpha',
			page: 3
		});
		expect(lireFiltresEntreprises(params('statut=ignoree')).statut).toBe('ignoree');
	});
	it('ignore un statut inconnu, une page invalide et une recherche vide', () => {
		expect(lireFiltresEntreprises(params('statut=nimporte&q=%20%20&page=abc'))).toEqual({
			statut: undefined,
			q: undefined,
			page: 1
		});
		expect(lireFiltresEntreprises(params('page=-4')).page).toBe(1);
		expect(lireFiltresEntreprises(params('page=2.5')).page).toBe(1);
	});
	it('borne la recherche à 100 caractères', () => {
		expect(lireFiltresEntreprises(params(`q=${'a'.repeat(300)}`)).q).toHaveLength(100);
	});
});

describe('lireFiltresOffres', () => {
	it('lit piste, seuil et page', () => {
		expect(lireFiltresOffres(params('piste=stage&seuil=sous&page=2'))).toEqual({ piste: 'stage', seuil: 'sous', page: 2 });
		expect(lireFiltresOffres(params('seuil=atteint')).seuil).toBe('atteint');
	});
	it('ignore les valeurs inconnues', () => {
		expect(lireFiltresOffres(params('piste=autre&seuil=haut&page=x'))).toEqual({
			piste: undefined,
			seuil: undefined,
			page: 1
		});
	});
});
