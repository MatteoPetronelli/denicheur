import { expect, test } from 'vitest';
import { niveauScore } from './score.js';

test.each([
	[40, 65, 'bas'],
	[64, 65, 'bas'],
	[65, 65, 'moyen'],
	[79, 65, 'moyen'],
	[80, 65, 'haut'],
	[0, 0, 'moyen']
] as const)('score %i avec un seuil de %i : %s', (score, min, attendu) => {
	expect(niveauScore(score, min)).toBe(attendu);
});
