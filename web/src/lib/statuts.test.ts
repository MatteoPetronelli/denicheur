import { expect, test } from 'vitest';
import { GROUPE_STATUT, LIBELLES } from './statuts.js';

test('chaque statut a exactement un groupe, et aucun groupe ne vise un statut inconnu', () => {
	expect(Object.keys(GROUPE_STATUT).sort()).toEqual(Object.keys(LIBELLES).sort());
	for (const groupe of Object.values(GROUPE_STATUT)) expect(['en-cours', 'positif', 'clos']).toContain(groupe);
});
