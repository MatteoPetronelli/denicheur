<script lang="ts">
	import { enhance } from '$app/forms';
	import type { SubmitFunction } from '$app/forms';
	import { tick } from 'svelte';
	import { envoi } from '#lib/envoi.js';
	import { niveauScore } from '#lib/score.js';
	import { atteignables, LIBELLES } from '#lib/statuts.js';
	import type { Carte } from '#lib/server/tableau.js';

	let {
		carte,
		scoreMin,
		erreur = null,
		suite = ''
	}: { carte: Carte; scoreMin: number; erreur?: string | null; suite?: string } = $props();

	const cle = $derived(`${carte.genre}-${carte.id}`);
	const choix = $derived(atteignables(carte.statut));
	const libelleLien = $derived(carte.genre === 'offre' ? "Voir l'offre" : 'Site de candidature');
	const niveau = $derived(carte.score === null ? null : niveauScore(carte.score, scoreMin));
	const TON = { haut: 'succes', moyen: 'en-cours', bas: 'avertissement' } as const;
	const SUFFIXE = { haut: ' · fort', moyen: '', bas: ' · sous le seuil' } as const;
	const libellePiste = (p: string) => (p === 'stage' ? 'Stage' : p === 'alternance' ? 'Alternance' : 'Autre');

	// Après un déplacement, la carte est recréée dans sa nouvelle colonne : le focus y est rendu.
	const deplacer: SubmitFunction = (entree) => {
		const suiteEnvoi = envoi(entree) as unknown as (o: { update: () => Promise<void> }) => Promise<void>;
		const id = `carte-${cle}`;
		return async (o) => {
			await suiteEnvoi(o);
			await tick();
			document.getElementById(id)?.focus();
		};
	};

	// Un seul menu ouvert à la fois.
	function fermerAutres(e: Event) {
		const d = e.currentTarget as HTMLDetailsElement;
		if (d.open) for (const autre of document.querySelectorAll<HTMLDetailsElement>('details.menu[open]')) if (autre !== d) autre.open = false;
	}
</script>

<article class="carte" id={`carte-${cle}`} tabindex="-1" aria-labelledby={`titre-${cle}`}>
	<h3 id={`titre-${cle}`}>
		<a class="etire" href={`/fiche/${carte.genre}/${carte.id}`}>{carte.titre}</a>
	</h3>
	{#if carte.entreprise}<p>{carte.entreprise}</p>{/if}
	{#if carte.activite || carte.commune}
		<p class="discret">{[carte.activite, carte.commune].filter(Boolean).join(' · ')}</p>
	{/if}
	<ul class="puces">
		{#if carte.score !== null && niveau}
			<li class={`badge ${TON[niveau]}`}>Score <span class="donnee">{carte.score}</span>{SUFFIXE[niveau]}</li>
		{/if}
		{#if carte.distance_km !== null}<li class="badge"><span class="donnee">{Math.round(carte.distance_km)}</span> km</li>{/if}
		{#if carte.piste}<li class="badge">{libellePiste(carte.piste)}</li>{/if}
		{#if carte.priorite !== null}<li class="badge">Priorité {carte.priorite}</li>{/if}
	</ul>
	{#if carte.lien || choix.length}
		<div class="pied">
			{#if carte.lien}
				<a class="externe" href={carte.lien} target="_blank" rel="noopener noreferrer">{libelleLien}<span aria-hidden="true"> ↗</span></a>
			{/if}
			{#if choix.length}
				<details class="menu" ontoggle={fermerAutres}>
					<summary>Déplacer</summary>
					<form method="POST" action={`?/statut${suite}`} use:enhance={deplacer}>
						<input type="hidden" name="genre" value={carte.genre} />
						<input type="hidden" name="id" value={carte.id} />
						<input type="hidden" name="titre" value={carte.titre} />
						{#each choix.filter((s) => s !== 'ignoree') as s (s)}
							<button type="submit" name="statut" value={s} class="btn-secondaire" aria-label={`Passer « ${carte.titre} » à ${LIBELLES[s]}`}>{LIBELLES[s]}</button>
						{/each}
						{#if choix.includes('ignoree')}
							<button type="submit" name="statut" value="ignoree" class="btn-discret ecarter" aria-label={`Passer « ${carte.titre} » à ${LIBELLES.ignoree}`}>{LIBELLES.ignoree}</button>
						{/if}
					</form>
				</details>
			{/if}
		</div>
	{/if}
	{#if erreur}<p class="erreur" role="alert">{erreur}</p>{/if}
</article>
