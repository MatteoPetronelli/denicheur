import type Database from 'better-sqlite3';

export type Resume = { offres: number; entreprises: number; suivis: number };

const compter = (db: Database.Database, table: string): number =>
	(db.prepare(`select count(*) as n from ${table}`).get() as { n: number }).n;

export function resume(db: Database.Database): Resume {
	return {
		offres: compter(db, 'offres'),
		entreprises: compter(db, 'entreprises'),
		suivis: compter(db, 'candidatures')
	};
}
