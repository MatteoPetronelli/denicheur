import { expect, test } from 'vitest';
import { pagesVisibles } from './pagination.js';

test.each([
	[1, 1, [1]],
	[1, 2, [1, 2]],
	[10, 24, [1, '…', 9, 10, 11, '…', 24]],
	[2, 24, [1, 2, 3, '…', 24]],
	[24, 24, [1, '…', 23, 24]],
	[3, 5, [1, 2, 3, 4, 5]],
	[99, 5, [1, '…', 4, 5]],
	[0, 5, [1, 2, '…', 5]]
] as const)('page %i sur %i', (page, total, attendu) => {
	expect(pagesVisibles(page, total)).toEqual(attendu);
});
