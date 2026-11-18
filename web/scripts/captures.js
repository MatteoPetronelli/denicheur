// Régénère les captures du README (docs/captures/) sur la base de démonstration synthétique.
import { spawnSync } from 'node:child_process';

const r = spawnSync('npx', ['playwright', 'test', 'e2e/captures.spec.ts'], {
	stdio: 'inherit',
	shell: true,
	env: { ...process.env, CAPTURES: '1' }
});
process.exit(r.status ?? 1);
