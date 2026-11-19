/** « — » pour une valeur absente ; 0 reste 0. */
export const ouTiret = (v: string | number | null | undefined): string => (v === null || v === undefined || v === '' ? '—' : String(v));
