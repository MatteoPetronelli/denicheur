/** Pages à proposer : la première, la dernière, la courante et ses voisines ; '…' marque chaque trou. */
export function pagesVisibles(page: number, total: number): (number | '…')[] {
	const n = Math.max(1, total);
	const p = Math.min(Math.max(1, page), n);
	const garder = [...new Set([1, p - 1, p, p + 1, n])].filter((x) => x >= 1 && x <= n).sort((a, b) => a - b);
	return garder.flatMap((x, i) => (i > 0 && x - garder[i - 1] > 1 ? ['…' as const, x] : [x]));
}
