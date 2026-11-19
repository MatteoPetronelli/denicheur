<script lang="ts">
	import { enhance } from '$app/forms';
	import { envoi } from '#lib/envoi.js';
	import { dateFr } from '#lib/dates.js';
	import Pagination from '#lib/components/Pagination.svelte';
	import { ouTiret } from '#lib/format.js';
	import { atteignables, GROUPE_STATUT, LIBELLES } from '#lib/statuts.js';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();

	function requete(page: number): string {
		const p = new URLSearchParams();
		if (data.filtres.statut) p.set('statut', data.filtres.statut);
		if (data.filtres.q) p.set('q', data.filtres.q);
		if (page > 1) p.set('page', String(page));
		return p.toString();
	}
	const lien = (page: number) => `/entreprises${requete(page) ? `?${requete(page)}` : ''}`;
	const suite = $derived(requete(data.liste.page) ? `&${requete(data.liste.page)}` : '');
	// Une seule liste d'en-têtes : le <thead> et les libellés des cellules en petit écran.
	const ENTETES = ['Entreprise', 'Distance', 'Priorité', 'Effectif', 'Suivi', 'Brouillons', 'Offre ouverte', 'Actions'];
	const erreurDe = (id: number) => (form && 'erreur' in form && form.genre === 'entreprise' && form.id === id ? form.erreur : null);
</script>

<svelte:head>
	<title>Entreprises · Dénicheur</title>
</svelte:head>

<h1>Entreprises</h1>

<form method="GET" class="filtres" aria-label="Filtres des entreprises">
	<label>
		Statut
		<select name="statut">
			<option value="" selected={!data.filtres.statut}>Tous</option>
			<option value="sans_suivi" selected={data.filtres.statut === 'sans_suivi'}>Sans suivi</option>
			{#each Object.entries(LIBELLES) as [valeur, libelle] (valeur)}
				<option value={valeur} selected={data.filtres.statut === valeur}>{libelle}</option>
			{/each}
		</select>
	</label>
	<label>
		Nom
		<input type="search" name="q" value={data.filtres.q ?? ''} maxlength="100" />
	</label>
	<button type="submit" class="btn-secondaire">Filtrer</button>
</form>

{#if form && 'ok' in form && form.ok}
	<p role="status" class="ok">Statut mis à jour.</p>
{/if}

<p class="discret">
	{data.liste.total} entreprise{data.liste.total > 1 ? 's' : ''} · page {data.liste.page} sur {data.liste.pages}
</p>

<div class="defile">
	<table class="liste">
		<caption class="sr-only">Entreprises, triées par priorité puis par distance</caption>
		<thead>
			<tr>
				{#each ENTETES as e, i (e)}<th scope="col" class:nombre={i >= 1 && i <= 3 || i === 5}>{e}</th>{/each}
			</tr>
		</thead>
		<tbody>
			{#each data.liste.lignes as e (e.id)}
				<tr>
					<th scope="row" data-libelle={ENTETES[0]}>
						<a href={`/fiche/entreprise/${e.id}`}>{e.nom}</a>
						{#if e.activite || e.commune}<span class="sous discret">{[e.activite, e.commune].filter(Boolean).join(' · ')}</span>{/if}
						{#if e.lien}<a class="sous" href={e.lien} target="_blank" rel="noopener noreferrer">Site de candidature<span aria-hidden="true"> ↗</span></a>{/if}
					</th>
					<td class="nombre donnee" data-libelle={ENTETES[1]}>{e.distance_km !== null ? `${Math.round(e.distance_km)} km` : '—'}</td>
					<td class="nombre donnee" data-libelle={ENTETES[2]}>{ouTiret(e.priorite)}</td>
					<td class="nombre donnee" data-libelle={ENTETES[3]}>{ouTiret(e.effectif)}</td>
					<td data-libelle={ENTETES[4]}>
						{#if e.statut}<span class={`badge ${GROUPE_STATUT[e.statut]}`}>{LIBELLES[e.statut]}</span>{:else}<span class="badge">Sans suivi</span>{/if}
						{#if e.contactee_le}<span class="sous discret">contactée le <span class="donnee">{dateFr(e.contactee_le)}</span></span>{/if}
					</td>
					<td class="nombre donnee" data-libelle={ENTETES[5]}>{e.nbBrouillons}</td>
					<td data-libelle={ENTETES[6]}>
						{#each e.offresOuvertes as o (o.id)}
							<a class="sous" href={`/fiche/offre/${o.id}`}>{o.titre}</a>
						{:else}
							<span class="discret" aria-label="aucune">—</span>
						{/each}
					</td>
					<td data-libelle={ENTETES[7]}>
						<form method="POST" action={`?/statut${suite}`} use:enhance={envoi} class="actions">
							<input type="hidden" name="genre" value="entreprise" />
							<input type="hidden" name="id" value={e.id} />
							{#if atteignables(e.statut).includes('candidature_envoyee')}
								<button type="submit" name="statut" value="candidature_envoyee" class="btn-secondaire" aria-label={`Marquer ${e.nom} comme contactée`}>Contactée</button>
							{/if}
							{#if atteignables(e.statut).includes('ignoree')}
								<button type="submit" name="statut" value="ignoree" class="btn-discret" aria-label={`Écarter ${e.nom}`}>Écarter</button>
							{/if}
						</form>
						{#if erreurDe(e.id)}<p class="erreur" role="alert">{erreurDe(e.id)}</p>{/if}
					</td>
				</tr>
			{:else}
				<tr><td colspan="8">Aucune entreprise ne correspond.</td></tr>
			{/each}
		</tbody>
	</table>
</div>

<Pagination page={data.liste.page} pages={data.liste.pages} {lien} />
