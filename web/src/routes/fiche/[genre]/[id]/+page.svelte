<script lang="ts">
	import { dateFr } from '#lib/dates.js';
	import { GROUPE_STATUT, LIBELLES } from '#lib/statuts.js';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	const c = $derived(data.carte);
	const libelleType: Record<string, string> = {
		email: 'E-mail de candidature',
		lettre: 'Lettre de motivation',
		relance: 'Relance',
		spontanee: 'Message spontané'
	};
</script>

<svelte:head>
	<title>{c.titre} · Dénicheur</title>
</svelte:head>

<nav aria-label="Fil d'Ariane" class="ariane">
	<ol>
		<li>{#if c.genre === 'offre'}<a href="/offres">Offres</a>{:else}<a href="/entreprises">Entreprises</a>{/if}</li>
		<li><span aria-current="page">{c.titre}</span></li>
	</ol>
</nav>
<h1>{c.titre}</h1>
<p class="genre discret">{c.genre === 'offre' ? 'Offre' : 'Entreprise'}</p>

<dl class="details">
	<dt>Statut</dt>
	<dd>{#if c.statut}<span class={`badge ${GROUPE_STATUT[c.statut]}`}>{LIBELLES[c.statut]}</span>{:else}<span class="badge">Nouvelle (sans suivi)</span>{/if}</dd>
	{#if c.entreprise}<dt>Entreprise</dt><dd>{c.entreprise}</dd>{/if}
	{#if c.activite}<dt>Activité</dt><dd>{c.activite}</dd>{/if}
	{#if c.commune}<dt>Commune</dt><dd>{c.commune}</dd>{/if}
	{#if c.score !== null}<dt>Score</dt><dd>{c.score}</dd>{/if}
	{#if c.distance_km !== null}<dt>Distance</dt><dd>{Math.round(c.distance_km)} km</dd>{/if}
	{#if c.priorite !== null}<dt>Priorité</dt><dd>{c.priorite}</dd>{/if}
	{#if data.dates?.listee_le}<dt>Proposée le</dt><dd>{dateFr(data.dates.listee_le)}</dd>{/if}
	{#if data.dates?.contactee_le}<dt>Contactée le</dt><dd>{dateFr(data.dates.contactee_le)}</dd>{/if}
	{#if data.dates?.ignoree_le}<dt>Écartée le</dt><dd>{dateFr(data.dates.ignoree_le)}</dd>{/if}
	{#if c.lien}
		<dt>Lien</dt>
		<dd><a href={c.lien} target="_blank" rel="noopener noreferrer">{c.genre === 'offre' ? "Voir l'offre" : 'Site de candidature'}</a></dd>
	{/if}
</dl>

{#if data.offresOuvertes.length}
	<h2>Offre ouverte aussi</h2>
	<ul>
		{#each data.offresOuvertes as o (o.id)}
			<li><a href={`/fiche/offre/${o.id}`}>{o.titre}</a></li>
		{/each}
	</ul>
{/if}

<h2>Brouillons ({data.brouillons.length})</h2>
{#each data.brouillons as b (b.id)}
	<article class="brouillon" aria-labelledby={`brouillon-${b.id}`}>
		<h3 id={`brouillon-${b.id}`}>{libelleType[b.type] ?? b.type}</h3>
		<p class="discret">
			Créé le {dateFr(b.cree_le)} · {b.gmail_draft ? 'déposé dans Gmail' : 'pas déposé dans Gmail'}
		</p>
		<pre>{b.contenu}</pre>
	</article>
{:else}
	<p class="discret">Aucun brouillon.</p>
{/each}
