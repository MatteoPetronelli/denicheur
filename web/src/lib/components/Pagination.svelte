<script lang="ts">
	import { pagesVisibles } from '#lib/pagination.js';

	let { page, pages, lien }: { page: number; pages: number; lien: (page: number) => string } = $props();
</script>

{#if pages > 1}
	<nav aria-label="Pages de la liste" class="pagination">
		{#if page > 1}<a href={lien(page - 1)} rel="prev" aria-label="Page précédente">← Précédente</a>{/if}
		<ol>
			{#each pagesVisibles(page, pages) as p, i (`${p}-${i}`)}
				<li>
					{#if p === '…'}
						<span class="discret" aria-hidden="true">…</span>
					{:else if p === page}
						<span class="courante" aria-current="page">{p}</span>
					{:else}
						<a href={lien(p)} aria-label={`Page ${p}`}>{p}</a>
					{/if}
				</li>
			{/each}
		</ol>
		{#if page < pages}<a href={lien(page + 1)} rel="next" aria-label="Page suivante">Suivante →</a>{/if}
	</nav>
{/if}
