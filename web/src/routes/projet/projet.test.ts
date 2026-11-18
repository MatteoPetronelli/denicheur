import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

const DOSSIER = import.meta.dirname;
const page = readFileSync(join(DOSSIER, '+page.svelte'), 'utf-8');
const texte = page.replace(/<script[\s\S]*?<\/script>/g, '').replace(/<[^>]+>/g, ' ');

describe('page projet : aucune donnée personnelle ni lecture de la base', () => {
	it('ne charge rien : ni load serveur, ni load universel, ni import de code serveur', () => {
		for (const f of ['+page.server.ts', '+page.ts', '+page.server.js', '+page.js']) {
			expect(existsSync(join(DOSSIER, f)), f).toBe(false);
		}
		expect(page).not.toMatch(/\$lib\/server|#lib\/server|better-sqlite3|process\.env/);
	});

	it('ne contient ni adresse e-mail, ni numéro de téléphone, ni chemin de disque, ni nom de fichier privé', () => {
		expect(texte).not.toMatch(/[\w.+-]+@[\w-]+\.[\w.]+/);
		expect(texte).not.toMatch(/(?:\+33|\b0)\s?[1-9](?:[\s.-]?\d{2}){4}\b/);
		expect(texte).not.toMatch(/\b[A-Za-z]:[\/]/);
		expect(texte).not.toMatch(/\/(?:Users|home)\//);
		expect(texte).not.toMatch(/identite\.md|liens\.md|cv_|CV_base|\.env|denicheur\.db|identifiants_/i);
	});

	it('annonce les garde-fous : envoi toujours humain, local et gratuit', () => {
		expect(texte).toContain("L'envoi reste humain");
		expect(texte).toContain('Tout est local et gratuit');
		expect(texte).toContain("j'envoie tout moi-même");
	});

	it('est en français', () => {
		expect(texte).toMatch(/\b(le|la|les|des|une|pour|avec)\b/);
		expect(page).toContain('<h1>');
	});
});
