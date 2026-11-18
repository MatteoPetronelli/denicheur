<script lang="ts">
	import { enhance } from '$app/forms';
	import { atteignables, LIBELLES } from '#lib/statuts.js';
	import type { Carte } from '#lib/server/tableau.js';

	let { carte, erreur = null, suite = '' }: { carte: Carte; erreur?: string | null; suite?: string } = $props();

	const cle = $derived(`${carte.genre}-${carte.id}`);
	const choix = $derived(atteignables(carte.statut));
	const libelleLien = $derived(carte.genre === 'offre' ? "Voir l'offre" : 'Site de candidature');
</script>

<article class="carte" aria-labelledby={`titre-${cle}`}>
	<h3 id={`titre-${cle}`}>
		<a href={`/fiche/${carte.genre}/${carte.id}`}>{carte.titre}</a>
	</h3>
	<p class="genre">{carte.genre === 'offre' ? 'Offre' : 'Entreprise'}</p>
	{#if carte.entreprise}<p>{carte.entreprise}</p>{/if}
	{#if carte.activite || carte.commune}
		<p class="discret">{[carte.activite, carte.commune].filter(Boolean).join(' · ')}</p>
	{/if}
	<ul class="puces">
		{#if carte.score !== null}<li>Score {carte.score}</li>{/if}
		{#if carte.distance_km !== null}<li>{Math.round(carte.distance_km)} km</li>{/if}
		{#if carte.piste}<li>{carte.piste === 'stage' ? 'Stage' : carte.piste === 'alternance' ? 'Alternance' : 'Autre'}</li>{/if}
		{#if carte.priorite !== null}<li>Priorité {carte.priorite}</li>{/if}
	</ul>
	{#if carte.lien}
		<p><a href={carte.lien} target="_blank" rel="noopener noreferrer">{libelleLien}</a></p>
	{/if}
	{#if choix.length}
		<form method="POST" action={`?/statut${suite}`} use:enhance>
			<input type="hidden" name="genre" value={carte.genre} />
			<input type="hidden" name="id" value={carte.id} />
			<label for={`statut-${cle}`}>Passer à</label>
			<select id={`statut-${cle}`} name="statut" required>
				<option value="">Choisir…</option>
				{#each choix as s (s)}<option value={s}>{LIBELLES[s]}</option>{/each}
			</select>
			<button type="submit">Changer</button>
		</form>
	{/if}
	{#if erreur}<p class="erreur" role="alert">{erreur}</p>{/if}
</article>
