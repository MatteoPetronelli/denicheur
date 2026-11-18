import { defineConfig } from '@playwright/test';
import { BASE_DEMO, CONFIG_DEMO, creerBaseDemo } from './e2e/graine';

// Base de démonstration synthétique recréée à chaque exécution : jamais la vraie base du Dénicheur.
if (!process.env.TEST_WORKER_INDEX) creerBaseDemo(); // seulement dans le processus principal

export default defineConfig({
	testDir: './e2e',
	timeout: 60_000,
	expect: { timeout: 10_000 },
	workers: 1, // les scénarios modifient la même base
	reporter: 'list',
	use: { baseURL: 'http://127.0.0.1:3456', viewport: { width: 1280, height: 900 } },
	webServer: {
		command: 'npm run build && npm start',
		url: 'http://127.0.0.1:3456',
		reuseExistingServer: false,
		timeout: 120_000,
		env: { DB_PATH: BASE_DEMO, CONFIG_PATH: CONFIG_DEMO, PORT: '3456' }
	}
});
