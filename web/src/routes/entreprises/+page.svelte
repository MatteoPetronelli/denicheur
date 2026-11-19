<script lang="ts">
	import { enhance } from '$app/forms';
	import { envoi } from '#lib/envoi.js';
	import { dateFr } from '#lib/dates.js';
	import { atteignables, LIBELLES } from '#lib/statuts.js';
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
	<button type="submit">Filtrer</button>
</form>

{#if form && 'ok' in form && form.ok}
	<p role="status" class="ok">Statut mis à jour.</p>
{/if}

<p class="discret">
	{data.liste.total} entreprise{data.liste.total > 1 ? 's' : ''} · page {data.liste.page} sur {data.liste.pages}
</p>

<div class="defile">
	<table>
		<caption class="sr-only">Entreprises, triées par priorité puis par distance</caption>
		<thead>
			<tr>
				<th scope="col">Nom</th>
				<th scope="col">Activité</th>
				<th scope="col">Commune</th>
				<th scope="col">Effectif</th>
				<th scope="col">Distance</th>
				<th scope="col">Priorité</th>
				<th scope="col">Statut</th>
				<th scope="col">Contactée le</th>
				<th scope="col">Brouillons</th>
				<th scope="col">Offre ouverte</th>
				<th scope="col">Actions</th>
			</tr>
		</thead>
		<tbody>
			{#each data.liste.lignes as e (e.id)}
				<tr>
					<th scope="row"><a href={`/fiche/entreprise/${e.id}`}>{e.nom}</a>
						{#if e.lien}<br /><a href={e.lien} target="_blank" rel="noopener noreferrer">Site de candidature</a>{/if}
					</th>
					<td>{e.activite ?? ''}</td>
					<td>{e.commune ?? ''}</td>
					<td class="donnee">{e.effectif ?? ''}</td>
					<td class="donnee">{e.distance_km !== null ? `${Math.round(e.distance_km)} km` : ''}</td>
					<td class="donnee">{e.priorite ?? ''}</td>
					<td>{e.statut ? LIBELLES[e.statut] : 'Sans suivi'}</td>
					<td class="donnee">{dateFr(e.contactee_le)}</td>
					<td class="donnee">{e.nbBrouillons}</td>
					<td>
						{#each e.offresOuvertes as o (o.id)}
							<a href={`/fiche/offre/${o.id}`}>{o.titre}</a><br />
						{/each}
					</td>
					<td>
						<form method="POST" action={`?/statut${suite}`} use:enhance={envoi} class="actions">
							<input type="hidden" name="genre" value="entreprise" />
							<input type="hidden" name="id" value={e.id} />
							{#if atteignables(e.statut).includes('candidature_envoyee')}
								<button type="submit" name="statut" value="candidature_envoyee" aria-label={`Marquer ${e.nom} comme contactée`}>Contactée</button>
							{/if}
							{#if atteignables(e.statut).includes('ignoree')}
								<button type="submit" name="statut" value="ignoree" class="btn-secondaire" aria-label={`Écarter ${e.nom}`}>Écarter</button>
							{/if}
						</form>
						{#if erreurDe(e.id)}<p class="erreur" role="alert">{erreurDe(e.id)}</p>{/if}
					</td>
				</tr>
			{:else}
				<tr><td colspan="11">Aucune entreprise ne correspond.</td></tr>
			{/each}
		</tbody>
	</table>
</div>

<nav aria-label="Pages de la liste" class="pagination">
	{#if data.liste.page > 1}<a href={lien(data.liste.page - 1)} rel="prev">← Page précédente</a>{/if}
	{#if data.liste.page < data.liste.pages}<a href={lien(data.liste.page + 1)} rel="next">Page suivante →</a>{/if}
</nav>
