<script lang="ts">
	import { dateFr } from '#lib/dates.js';
	import { formaterDuree } from '#lib/duree.js';
	import { etapes, pourcent } from '#lib/entonnoir.js';
	import { LIBELLES, type Statut } from '#lib/statuts.js';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	const s = $derived(data.stats);
	const statuts = Object.keys(LIBELLES) as Statut[];
	const entonnoir = $derived(etapes(s.offres));
	// Échelle commune aux barres de la répartition ; au moins 1 pour ne jamais diviser par zéro.
	const maximum = $derived(Math.max(1, ...statuts.flatMap((st) => [s.candidatures.offres[st], s.candidatures.entreprises[st]])));
</script>

<svelte:head>
	<title>Statistiques · Dénicheur</title>
</svelte:head>

<h1>Statistiques</h1>

<h2>Offres</h2>
<ol class="entonnoir">
	{#each entonnoir as e (e.cle)}
		<li>
			<span class="barre" aria-hidden="true" style={`--part: ${e.part ?? 0}`}></span>
			<span class="valeur"><span class="nombre">{e.valeur}</span> {e.cle === 'vues' ? 'offres vues' : e.libelle}</span>
			{#if e.cle !== 'vues'}
				<span class="discret taux">{pourcent(e.part)} des vues · {pourcent(e.taux)} de l'étape précédente</span>
			{/if}
		</li>
	{/each}
</ol>

<h2>Candidatures</h2>
<ul class="cartes">
	<li class="principale">
		<span class="nombre">{s.reponses.total}</span> réponses (entretien, offre ou refus)
		<span class="ventilation"><span class="donnee">{s.reponses.offres}</span> sur des offres · <span class="donnee">{s.reponses.entreprises}</span> sur des entreprises</span>
	</li>
</ul>

<h3>Par statut</h3>
<dl class="repartition">
	{#each statuts as statut (statut)}
		{@const o = s.candidatures.offres[statut]}
		{@const en = s.candidatures.entreprises[statut]}
		<div class:vide={o + en === 0}>
			<dt>{LIBELLES[statut]}</dt>
			<dd class="offres"><span class="barre" aria-hidden="true" style={`--part: ${o / maximum}`}></span>Offres <span class="donnee">{o}</span></dd>
			<dd class="entreprises"><span class="barre" aria-hidden="true" style={`--part: ${en / maximum}`}></span>Entreprises <span class="donnee">{en}</span></dd>
		</div>
	{/each}
</dl>

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
				<th scope="col" class="nombre">Collectées</th>
				<th scope="col" class="nombre">Retenues</th>
				<th scope="col" class="nombre">Notées</th>
				<th scope="col" class="nombre">Envoyées</th>
				<th scope="col" class="nombre">Modèle</th>
				<th scope="col">Erreurs</th>
			</tr>
		</thead>
		<tbody>
			{#each s.dernieres as e (e.id)}
				<tr>
					<th scope="row" class="donnee">{dateFr(e.debut)}</th>
					<td><span class="badge">{e.mode}</span></td>
					<td class="nombre donnee">{e.collectees}</td>
					<td class="nombre donnee">{e.retenues}</td>
					<td class="nombre donnee">{e.scorees}</td>
					<td class="nombre donnee">{e.notifiees}</td>
					<td class="nombre donnee">{formaterDuree(e.duree_llm_s)}</td>
					<td>
						{#if e.nbErreurs}
							<span class="badge danger" title="Détail dans les journaux">{e.nbErreurs} erreur{e.nbErreurs > 1 ? 's' : ''}</span><span class="discret">, détail dans les journaux</span>
						{:else}
							<span class="discret">aucune</span>
						{/if}
					</td>
				</tr>
			{:else}
				<tr><td colspan="8">Aucune exécution enregistrée.</td></tr>
			{/each}
		</tbody>
	</table>
</div>
