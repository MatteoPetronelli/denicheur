import { expect, test } from 'vitest';
import { ouTiret } from './format.js';

test('valeur absente : tiret ; zéro et texte : tels quels', () => {
	expect([null, undefined, ''].map(ouTiret)).toEqual(['—', '—', '—']);
	expect(ouTiret(0)).toBe('0');
	expect(ouTiret('Versailles')).toBe('Versailles');
});
