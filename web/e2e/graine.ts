// Jeu de données synthétique pour les tests de navigateur : aucune donnée de la vraie base.
import { execFileSync } from 'node:child_process';
import { mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import Database from 'better-sqlite3';
import { ajouterEntreprise, ajouterOffre, ajouterScore } from '../src/lib/server/donnees-de-test';

const WEB = resolve(import.meta.dirname, '..');
export const DOSSIER = join(WEB, '.e2e');
export const BASE_DEMO = join(DOSSIER, 'demo.db');
export const CONFIG_DEMO = join(DOSSIER, 'recherches.yaml');
export const SIRET_BETA = '22222222200011';

const NOTIFIEE = '2026-11-18 08:00:00.000000';
const MAINTENANT = '2026-11-18 09:00:00.000000';

/** Recrée la base : migrations par Python, puis offres, entreprises et un brouillon. */
export function creerBaseDemo(): void {
	mkdirSync(DOSSIER, { recursive: true });
	for (const suffixe of ['', '-wal', '-shm']) rmSync(BASE_DEMO + suffixe, { force: true });
	execFileSync('py', [join(WEB, 'tests/creer_base.py'), BASE_DEMO], { cwd: resolve(WEB, '..') });
	writeFileSync(CONFIG_DEMO, 'score_min: 65\n', 'utf-8');

	const db = new Database(BASE_DEMO);
	try {
		const offre = (titre: string, entreprise: string, piste: 'stage' | 'alternance', score: number, siret?: string) => {
			const id = ajouterOffre(db, { titre, entreprise, piste, distance_km: 12, notifiee_le: NOTIFIEE, siret: siret ?? null });
			ajouterScore(db, id, score, piste);
			return id;
		};
		offre('Développeur web en alternance', 'ACME', 'alternance', 82);
		offre('Stage analyse de données', 'Data Atelier', 'stage', 70);
		offre('Stage support informatique', 'Petite Boîte', 'stage', 40);
		offre('Développeur full stack', 'Beta SA', 'alternance', 75, SIRET_BETA);

		ajouterEntreprise(db, { nom: 'Alpha Soft', priorite: 1, distance_km: 3, activite: 'Programmation informatique', commune: 'Marly-le-Roi', url_candidature: 'https://alpha.example/emplois' });
		const beta = ajouterEntreprise(db, { nom: 'Beta SA', siret: SIRET_BETA, priorite: 2, distance_km: 8, activite: 'Conseil en systèmes', commune: 'Versailles' });
		for (let i = 1; i <= 58; i++) {
			ajouterEntreprise(db, { nom: `Société ${String(i).padStart(2, '0')}`, priorite: i + 2, distance_km: 10 + i });
		}
		db.prepare("insert into candidatures (entreprise_id, statut, cree_le, maj_le) values (?, 'interessante', ?, ?)").run(beta, MAINTENANT, MAINTENANT);
		db.prepare("insert into brouillons (candidature_id, type, contenu, gmail_draft, cree_le) values (1, 'spontanee', ?, 0, ?)").run(
			'Bonjour,\nJe vous écris pour une alternance. <script>window.__xss = 1</script>',
			MAINTENANT
		);
	} finally {
		db.close();
	}
}
