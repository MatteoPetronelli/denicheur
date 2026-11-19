export type NiveauScore = 'haut' | 'moyen' | 'bas';

/** Haut à partir de 15 points au-dessus du seuil `score_min`, bas en dessous du seuil. */
export function niveauScore(score: number, scoreMin: number): NiveauScore {
	if (score < scoreMin) return 'bas';
	return score >= scoreMin + 15 ? 'haut' : 'moyen';
}
