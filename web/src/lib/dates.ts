const FORMAT = new Intl.DateTimeFormat('fr-FR', {
	timeZone: 'Europe/Paris',
	day: '2-digit',
	month: '2-digit',
	year: 'numeric',
	hour: '2-digit',
	minute: '2-digit'
});

/** Date de la base (UTC sans fuseau, comme l'écrit SQLAlchemy) affichée à l'heure de Paris ; vide si absente. */
export function dateFr(valeur: string | null | undefined): string {
	if (!valeur) return '';
	const d = new Date(`${valeur.replace(' ', 'T')}Z`);
	return Number.isNaN(d.getTime()) ? '' : FORMAT.format(d).replace(',', '');
}
