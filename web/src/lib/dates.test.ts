import { expect, it } from 'vitest';
import { dateFr } from './dates.js';

it('affiche une date UTC de la base à l’heure de Paris', () => {
	expect(dateFr('2026-11-18 09:00:00.000000')).toBe('18/11/2026 10:00'); // hiver : UTC+1
	expect(dateFr('2026-07-01 09:00:00.000000')).toBe('01/07/2026 11:00'); // été : UTC+2
});

it('renvoie une chaîne vide sans date ou avec une date illisible', () => {
	expect(dateFr(null)).toBe('');
	expect(dateFr(undefined)).toBe('');
	expect(dateFr('pas une date')).toBe('');
});
