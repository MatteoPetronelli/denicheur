<script lang="ts">
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
</script>

<svelte:head>
	<title>Accueil · Dénicheur</title>
</svelte:head>

<h1>Tableau de bord du Dénicheur</h1>
<p class="discret">Base connectée. Le tableau des candidatures arrive avec le lot suivant.</p>
<ul class="cartes">
	<li><span class="nombre">{data.resume.offres}</span> offres</li>
	<li><span class="nombre">{data.resume.entreprises}</span> entreprises</li>
	<li><span class="nombre">{data.resume.suivis}</span> candidatures suivies</li>
</ul>
