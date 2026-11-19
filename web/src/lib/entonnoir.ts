export type Etape = { cle: string; libelle: string; valeur: number; part: number | null; taux: number | null };

type Offres = { vues: number; retenues: number; notees: number; notifiees: number };

/** Étapes de l'entonnoir : part des offres vues et taux depuis l'étape précédente, `null` si le dénominateur est nul. */
export function etapes(o: Offres): Etape[] {
	const liste = [
		{ cle: 'vues', libelle: 'vues', valeur: o.vues },
		{ cle: 'retenues', libelle: 'retenues par le préfiltre', valeur: o.retenues },
		{ cle: 'notees', libelle: 'notées par le modèle', valeur: o.notees },
		{ cle: 'notifiees', libelle: 'envoyées sur Telegram', valeur: o.notifiees }
	];
	const div = (a: number, b: number) => (b > 0 ? a / b : null);
	return liste.map((e, i) => ({ ...e, part: div(e.valeur, o.vues), taux: i === 0 ? null : div(e.valeur, liste[i - 1].valeur) }));
}

/** 0,667 → « 67 % » ; `null` → « — ». */
export const pourcent = (x: number | null): string => (x === null ? '—' : `${Math.round(x * 100)} %`);
