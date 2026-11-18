import { existsSync } from 'node:fs';
import { resolve } from 'node:path';
import Database from 'better-sqlite3';

export class ErreurBase extends Error {}

const TABLES = ['offres', 'scores', 'candidatures', 'entreprises', 'brouillons', 'executions', 'parametres'];

/** Ouvre la base du Dénicheur sans jamais la créer ni la migrer : le schéma appartient à Python. */
export function ouvrir(chemin: string): Database.Database {
	let db: Database.Database;
	try {
		db = new Database(chemin, { fileMustExist: true });
	} catch {
		throw new ErreurBase(
			existsSync(chemin) ? `Base illisible : ${chemin}` : `Base introuvable : ${chemin}`
		);
	}
	try {
		db.pragma('busy_timeout = 5000');
		db.pragma('foreign_keys = ON');
		const presentes = new Set(
			(db.prepare("select name from sqlite_master where type = 'table'").all() as { name: string }[]).map(
				(t) => t.name
			)
		);
		const manquantes = TABLES.filter((t) => !presentes.has(t));
		if (manquantes.length) {
			throw new ErreurBase(`Schéma inattendu : table « ${manquantes[0]} » absente. Lance « py -m denicheur init-db ».`);
		}
	} catch (e) {
		db.close();
		if (e instanceof ErreurBase) throw e;
		throw new ErreurBase(`Base illisible : ${chemin}`);
	}
	return db;
}

export function cheminBase(): string {
	return resolve(process.env.DB_PATH ?? '../denicheur.db');
}

let connexion: Database.Database | null = null;

export function fermer(): void {
	connexion?.close();
	connexion = null;
}

/** Une seule connexion par processus, ouverte à la première demande. */
export function base(): Database.Database {
	connexion ??= ouvrir(cheminBase());
	return connexion;
}
