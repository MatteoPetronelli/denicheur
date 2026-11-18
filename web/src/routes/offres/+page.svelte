<script lang="ts">
	import { LIBELLES } from '#lib/statuts.js';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	function requete(page: number): string {
		const p = new URLSearchParams();
		if (data.filtres.piste) p.set('piste', data.filtres.piste);
		if (data.filtres.seuil) p.set('seuil', data.filtres.seuil);
		if (page > 1) p.set('page', String(page));
		return p.toString();
	}
	const lien = (page: number) => `/offres${requete(page) ? `?${requete(page)}` : ''}`;
	const libellePiste = { stage: 'Stage', alternance: 'Alternance', autre: 'Autre' } as const;
</script>

<svelte:head>
	<title>Offres · Dénicheur</title>
</svelte:head>

<h1>Offres notées</h1>
<p class="discret">
	Seuil de score de la configuration : {data.scoreMin}. Les offres rejetées par le préfiltre n'apparaissent pas ici.
</p>

<form method="GET" class="filtres" aria-label="Filtres des offres">
	<label>
		Piste
		<select name="piste">
			<option value="" selected={!data.filtres.piste}>Toutes</option>
			<option value="stage" selected={data.filtres.piste === 'stage'}>Stage</option>
			<option value="alternance" selected={data.filtres.piste === 'alternance'}>Alternance</option>
		</select>
	</label>
	<label>
		Score
		<select name="seuil">
			<option value="" selected={!data.filtres.seuil}>Tous</option>
			<option value="atteint" selected={data.filtres.seuil === 'atteint'}>Seuil atteint</option>
			<option value="sous" selected={data.filtres.seuil === 'sous'}>Sous le seuil</option>
		</select>
	</label>
	<button type="submit">Filtrer</button>
</form>

<p class="discret">
	{data.liste.total} offre{data.liste.total > 1 ? 's' : ''} · page {data.liste.page} sur {data.liste.pages}
</p>

<div class="defile">
	<table>
		<caption class="sr-only">Offres notées, par score décroissant</caption>
		<thead>
			<tr>
				<th scope="col">Offre</th>
				<th scope="col">Entreprise</th>
				<th scope="col">Piste</th>
				<th scope="col">Score</th>
				<th scope="col">Distance</th>
				<th scope="col">Suivi</th>
			</tr>
		</thead>
		<tbody>
			{#each data.liste.lignes as o (o.id)}
				<tr>
					<th scope="row">
						<a href={`/fiche/offre/${o.id}`}>{o.titre}</a>
						{#if o.lien}<br /><a href={o.lien} target="_blank" rel="noopener noreferrer">Voir l'offre</a>{/if}
					</th>
					<td>{o.entreprise ?? ''}</td>
					<td>{libellePiste[o.piste]}</td>
					<td>{o.score}{#if o.sousSeuil} <span class="etiquette">sous le seuil</span>{/if}</td>
					<td>{o.distance_km !== null ? `${Math.round(o.distance_km)} km` : ''}</td>
					<td>{o.statut ? LIBELLES[o.statut] : 'Sans suivi'}</td>
				</tr>
			{:else}
				<tr><td colspan="6">Aucune offre ne correspond.</td></tr>
			{/each}
		</tbody>
	</table>
</div>

<nav aria-label="Pages de la liste" class="pagination">
	{#if data.liste.page > 1}<a href={lien(data.liste.page - 1)} rel="prev">← Page précédente</a>{/if}
	{#if data.liste.page < data.liste.pages}<a href={lien(data.liste.page + 1)} rel="next">Page suivante →</a>{/if}
</nav>
