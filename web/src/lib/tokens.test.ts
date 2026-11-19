import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { expect, test } from 'vitest';

// Spec dashboard-design « Design tokens only » : les couleurs vivent dans app.css, jamais dans les pages.
const RACINE = join(import.meta.dirname, '..');
const COULEUR = /#[0-9a-f]{3,8}\b|rgba?\(|hsla?\(/i;

function fichiersSvelte(dossier: string): string[] {
	return readdirSync(dossier, { withFileTypes: true }).flatMap((e) =>
		e.isDirectory() ? fichiersSvelte(join(dossier, e.name)) : e.name.endsWith('.svelte') ? [join(dossier, e.name)] : []
	);
}

test('aucune couleur littérale dans les fichiers .svelte', () => {
	const fichiers = fichiersSvelte(RACINE);
	expect(fichiers.length).toBeGreaterThan(5);
	const fautifs = fichiers.filter((f) => COULEUR.test(readFileSync(f, 'utf8')));
	expect(fautifs).toEqual([]);
});
