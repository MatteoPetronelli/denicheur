<script lang="ts">
	import '../app.css';
	import favicon from '#lib/assets/favicon.svg';
	import { page } from '$app/state';
	import type { LayoutProps } from './$types';

	let { children }: LayoutProps = $props();

	// Une page s'ajoute ici quand elle existe : jamais de lien mort.
	const pages = [{ chemin: '/', libelle: 'Accueil' }];
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<a class="saut" href="#contenu">Aller au contenu</a>
<header class="haut">
	<div class="contenu">
		<strong>Dénicheur</strong>
		<nav aria-label="Pages du tableau de bord">
			{#each pages as p (p.chemin)}
				<a href={p.chemin} aria-current={page.url.pathname === p.chemin ? 'page' : undefined}>{p.libelle}</a>
			{/each}
		</nav>
	</div>
</header>
<main id="contenu">
	{@render children()}
</main>
