import donnees from './transitions.json';

export type Statut = keyof typeof donnees.libelles;

export const LIBELLES: Record<Statut, string> = donnees.libelles;
/** Colonnes du tableau, dans l'ordre ; « ignoree » n'en a pas (masquée par défaut). */
export const COLONNES = donnees.colonnes as Statut[];

const TRANSITIONS: Record<string, string[]> = donnees.transitions;

export function estStatut(valeur: unknown): valeur is Statut {
	return typeof valeur === 'string' && Object.hasOwn(LIBELLES, valeur);
}

/** Statuts atteignables depuis `courant` (null = nouvelle, sans suivi). */
export function atteignables(courant: Statut | null): Statut[] {
	return (TRANSITIONS[courant ?? 'nouvelle'] ?? []) as Statut[];
}

export type Groupe = 'en-cours' | 'positif' | 'clos';

/** Groupe visuel de chaque statut (pastilles et badges) : trois tons plutôt qu'une couleur par statut. */
export const GROUPE_STATUT: Record<Statut, Groupe> = {
	interessante: 'en-cours',
	candidature_envoyee: 'en-cours',
	relancee: 'en-cours',
	entretien: 'positif',
	offre: 'positif',
	refus: 'clos',
	sans_reponse: 'clos',
	ignoree: 'clos'
};
