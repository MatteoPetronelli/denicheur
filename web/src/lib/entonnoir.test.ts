import { expect, test } from 'vitest';
import { etapes, pourcent } from './entonnoir.js';

test('parts et taux de l’entonnoir', () => {
	const e = etapes({ vues: 40, retenues: 12, notees: 12, notifiees: 8 });
	expect(e.map((x) => x.part)).toEqual([1, 0.3, 0.3, 0.2]);
	expect(e.map((x) => x.taux && Math.round(x.taux * 1000) / 1000)).toEqual([null, 0.3, 1, 0.667]);
});

test('base vide : ni NaN ni Infinity, tout à null', () => {
	const e = etapes({ vues: 0, retenues: 0, notees: 0, notifiees: 0 });
	expect(e.map((x) => [x.part, x.taux])).toEqual([[null, null], [null, null], [null, null], [null, null]]);
});

test('affichage en pourcentage', () => {
	expect([pourcent(null), pourcent(0.667), pourcent(0.3), pourcent(1)]).toEqual(['—', '67 %', '30 %', '100 %']);
});
