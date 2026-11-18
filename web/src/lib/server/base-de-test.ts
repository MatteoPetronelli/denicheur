// Aide de test : une vraie base migrée par Python, jamais un schéma recopié ici.
import { execFileSync } from 'node:child_process';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';

const RACINE = resolve(import.meta.dirname, '../../../..');

export function creerBase(): { chemin: string; nettoyer: () => void } {
	const dossier = mkdtempSync(join(tmpdir(), 'denicheur-web-'));
	const chemin = join(dossier, 'test.db');
	execFileSync('py', [join(RACINE, 'web/tests/creer_base.py'), chemin], { cwd: RACINE });
	return { chemin, nettoyer: () => rmSync(dossier, { recursive: true, force: true }) };
}
