/** Durée en secondes lisible : « 45 s », « 1 min 15 s ». */
export function formaterDuree(secondes: number): string {
	const total = Math.round(secondes);
	if (total < 60) return `${total} s`;
	const minutes = Math.floor(total / 60);
	const reste = total % 60;
	return reste ? `${minutes} min ${reste} s` : `${minutes} min`;
}
