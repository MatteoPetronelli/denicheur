import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { defineConfig } from '@playwright/test';

// Base de démonstration synthétique, créée par Python : jamais la vraie base du Dénicheur.
const dossier = resolve(import.meta.dirname, '.e2e');
export const BASE_DEMO = join(dossier, 'demo.db');
if (!existsSync(BASE_DEMO)) {
	mkdirSync(dossier, { recursive: true });
	execFileSync('py', [resolve(import.meta.dirname, 'tests/creer_base.py'), BASE_DEMO], {
		cwd: resolve(import.meta.dirname, '..')
	});
}

export default defineConfig({
	testDir: './e2e',
	timeout: 60_000,
	expect: { timeout: 10_000 },
	workers: 1,
	reporter: 'list',
	use: { baseURL: 'http://127.0.0.1:3456', viewport: { width: 1280, height: 900 } },
	webServer: {
		command: 'npm run build && npm start',
		url: 'http://127.0.0.1:3456',
		reuseExistingServer: false,
		timeout: 120_000,
		env: { DB_PATH: BASE_DEMO, PORT: '3456' }
	}
});
