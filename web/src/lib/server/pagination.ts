export const PAR_PAGE = 50;

/** Nombre de pages et page demandée ramenée dans les limites (invalide = première). */
export function borner(total: number, demandee: number | undefined): { pages: number; page: number } {
	const pages = Math.max(1, Math.ceil(total / PAR_PAGE));
	const page = Math.min(pages, Math.max(1, Number.isInteger(demandee) ? (demandee as number) : 1));
	return { pages, page };
}
