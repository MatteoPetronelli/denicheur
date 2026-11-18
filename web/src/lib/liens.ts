/** Un lien venu de la base n'est repris que s'il commence par http(s) : jamais `javascript:` ni autre schéma. */
export function lienSur(url: string | null | undefined): string | null {
	return url && /^https?:\/\//i.test(url) ? url : null;
}
