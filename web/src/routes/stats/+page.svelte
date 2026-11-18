<script lang="ts">
	import { dateFr } from '#lib/dates.js';
	import { formaterDuree } from '#lib/duree.js';
	import { LIBELLES, type Statut } from '#lib/statuts.js';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	const s = $derived(data.stats);
	const statuts = Object.keys(LIBELLES) as Statut[];
</script>

<svelte:head>
	<title>Statistiques · Dénicheur</title>
</svelte:head>

<h1>Statistiques</h1>

<h2>Offres</h2>
<ul class="cartes">
	<li><span class="nombre">{s.offres.vues}</span> offres vues</li>
	<li><span class="nombre">{s.offres.retenues}</span> retenues par le préfiltre</li>
	<li><span class="nombre">{s.offres.notees}</span> notées par le modèle</li>
	<li><span class="nombre">{s.offres.notifiees}</span> envoyées sur Telegram</li>
</ul>

<h2>Candidatures</h2>
<ul class="cartes">
	<li><span class="nombre">{s.reponses.total}</span> réponses (entretien, offre ou refus)</li>
	<li><span class="nombre">{s.reponses.offres}</span> sur des offres</li>
	<li><span class="nombre">{s.reponses.entreprises}</span> sur des entreprises</li>
</ul>
<div class="defile">
	<table class="etroit">
		<caption class="sr-only">Candidatures par statut, offres et entreprises séparées</caption>
		<thead>
			<tr>
				<th scope="col">Statut</th>
				<th scope="col">Offres</th>
				<th scope="col">Entreprises</th>
			</tr>
		</thead>
		<tbody>
			{#each statuts as statut (statut)}
				<tr>
					<th scope="row">{LIBELLES[statut]}</th>
					<td>{s.candidatures.offres[statut]}</td>
					<td>{s.candidatures.entreprises[statut]}</td>
				</tr>
			{/each}
		</tbody>
	</table>
</div>

<h2>Modèle local</h2>
<ul class="cartes">
	<li><span class="nombre">{s.llm.executions}</span> exécutions enregistrées</li>
	<li><span class="nombre">{formaterDuree(s.llm.moyenne_s)}</span> de modèle par exécution en moyenne</li>
	<li><span class="nombre">{formaterDuree(s.llm.total_s)}</span> de modèle au total</li>
</ul>

<h2>Dernières exécutions</h2>
<div class="defile">
	<table>
		<caption class="sr-only">Les dix dernières exécutions, la plus récente en premier</caption>
		<thead>
			<tr>
				<th scope="col">Début</th>
				<th scope="col">Mode</th>
				<th scope="col">Collectées</th>
				<th scope="col">Retenues</th>
				<th scope="col">Notées</th>
				<th scope="col">Envoyées</th>
				<th scope="col">Modèle</th>
				<th scope="col">Erreurs</th>
			</tr>
		</thead>
		<tbody>
			{#each s.dernieres as e (e.id)}
				<tr>
					<th scope="row">{dateFr(e.debut)}</th>
					<td>{e.mode}</td>
					<td>{e.collectees}</td>
					<td>{e.retenues}</td>
					<td>{e.scorees}</td>
					<td>{e.notifiees}</td>
					<td>{formaterDuree(e.duree_llm_s)}</td>
					<td>
						{#if e.nbErreurs}
							{e.nbErreurs} erreur{e.nbErreurs > 1 ? 's' : ''}, détail dans les journaux
						{:else}
							aucune
						{/if}
					</td>
				</tr>
			{:else}
				<tr><td colspan="8">Aucune exécution enregistrée.</td></tr>
			{/each}
		</tbody>
	</table>
</div>
