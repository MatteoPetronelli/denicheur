import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { parse } from 'yaml';

export class ErreurConfig extends Error {}

export function cheminConfig(): string {
	return resolve(process.env.CONFIG_PATH ?? '../config/recherches.yaml');
}

/** Seuil de score de la configuration du Dénicheur : lu, jamais recopié ni inventé. */
export function lireScoreMin(chemin: string = cheminConfig()): number {
	let texte: string;
	try {
		texte = readFileSync(chemin, 'utf-8');
	} catch {
		throw new ErreurConfig(`Configuration introuvable : ${chemin}`);
	}
	let donnees: unknown;
	try {
		donnees = parse(texte);
	} catch {
		throw new ErreurConfig('Configuration illisible : score_min inaccessible.');
	}
	const valeur = (donnees as { score_min?: number } | null)?.score_min as number;
	if (!Number.isInteger(valeur) || valeur < 0 || valeur > 100) {
		throw new ErreurConfig('Configuration invalide : score_min doit être un entier entre 0 et 100.');
	}
	return valeur;
}
