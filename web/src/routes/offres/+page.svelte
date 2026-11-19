<script lang="ts">
	import Pagination from '#lib/components/Pagination.svelte';
	import { GROUPE_STATUT, LIBELLES } from '#lib/statuts.js';
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
	const ENTETES = ['Offre', 'Piste', 'Score', 'Distance', 'Suivi'];
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
	<button type="submit" class="btn-secondaire">Filtrer</button>
</form>

<p class="discret">
	{data.liste.total} offre{data.liste.total > 1 ? 's' : ''} · page {data.liste.page} sur {data.liste.pages}
</p>

<div class="defile">
	<table class="liste">
		<caption class="sr-only">Offres notées, par score décroissant</caption>
		<thead>
			<tr>
				{#each ENTETES as e, i (e)}<th scope="col" class:nombre={i === 2 || i === 3}>{e}</th>{/each}
			</tr>
		</thead>
		<tbody>
			{#each data.liste.lignes as o (o.id)}
				<tr>
					<th scope="row" data-libelle={ENTETES[0]}>
						<a href={`/fiche/offre/${o.id}`}>{o.titre}</a>
						<span class="sous discret">{o.entreprise ?? '—'}</span>
						{#if o.lien}<a class="sous" href={o.lien} target="_blank" rel="noopener noreferrer">Voir l'offre<span aria-hidden="true"> ↗</span></a>{/if}
					</th>
					<td data-libelle={ENTETES[1]}>{libellePiste[o.piste]}</td>
					<td class="nombre" data-libelle={ENTETES[2]}>
						<span class="donnee">{o.score}</span>{#if o.sousSeuil}<span class="badge avertissement seuil">sous le seuil</span>{/if}
					</td>
					<td class="nombre donnee" data-libelle={ENTETES[3]}>{o.distance_km !== null ? `${Math.round(o.distance_km)} km` : '—'}</td>
					<td data-libelle={ENTETES[4]}>
						{#if o.statut}<span class={`badge ${GROUPE_STATUT[o.statut]}`}>{LIBELLES[o.statut]}</span>{:else}<span class="badge">Sans suivi</span>{/if}
					</td>
				</tr>
			{:else}
				<tr><td colspan="5">Aucune offre ne correspond.</td></tr>
			{/each}
		</tbody>
	</table>
</div>

<Pagination page={data.liste.page} pages={data.liste.pages} {lien} />
