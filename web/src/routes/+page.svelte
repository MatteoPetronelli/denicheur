<script lang="ts">
	import CarteSuivi from '#lib/components/CarteSuivi.svelte';
	import { COLONNES, LIBELLES } from '#lib/statuts.js';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();

	const colonnes = $derived(COLONNES.map((s) => ({ statut: s, cartes: data.tableau.colonnes[s] ?? [] })));
	const suite = $derived(
		[
			data.filtres.piste && `piste=${data.filtres.piste}`,
			data.filtres.nature && `nature=${data.filtres.nature}`,
			data.filtres.ecartees && 'ecartees=1'
		]
			.filter(Boolean)
			.map((p) => `&${p}`)
			.join('')
	);
	const erreurDe = (genre: string, id: number) => (form && 'erreur' in form && form.genre === genre && form.id === id ? form.erreur : null);
</script>

<svelte:head>
	<title>Candidatures · Dénicheur</title>
</svelte:head>

<h1>Candidatures</h1>

<form method="GET" class="filtres" aria-label="Filtres du tableau">
	<label>
		Piste
		<select name="piste">
			<option value="" selected={!data.filtres.piste}>Toutes</option>
			<option value="stage" selected={data.filtres.piste === 'stage'}>Stage</option>
			<option value="alternance" selected={data.filtres.piste === 'alternance'}>Alternance</option>
		</select>
	</label>
	<label>
		Nature
		<select name="nature">
			<option value="" selected={!data.filtres.nature}>Offres et entreprises</option>
			<option value="offre" selected={data.filtres.nature === 'offre'}>Offres</option>
			<option value="entreprise" selected={data.filtres.nature === 'entreprise'}>Entreprises</option>
		</select>
	</label>
	<label class="case">
		<input type="checkbox" name="ecartees" value="1" checked={data.filtres.ecartees} />
		Afficher les écartées ({data.tableau.nbEcartees})
	</label>
	<button type="submit">Filtrer</button>
</form>

{#if form && 'ok' in form && form.ok}
	<p role="status" class="ok">Statut mis à jour.</p>
{/if}

<div class="tableau">
	<section aria-labelledby="col-nouvelles">
		<h2 id="col-nouvelles">Nouvelles ({data.tableau.nouvelles.length})</h2>
		{#each data.tableau.nouvelles as carte (`${carte.genre}-${carte.id}`)}
			<CarteSuivi {carte} {suite} erreur={erreurDe(carte.genre, carte.id)} />
		{:else}
			<p class="discret">Rien de nouveau.</p>
		{/each}
	</section>
	{#each colonnes as col (col.statut)}
		<section aria-labelledby={`col-${col.statut}`}>
			<h2 id={`col-${col.statut}`}>{LIBELLES[col.statut]} ({col.cartes.length})</h2>
			{#each col.cartes as carte (`${carte.genre}-${carte.id}`)}
				<CarteSuivi {carte} {suite} erreur={erreurDe(carte.genre, carte.id)} />
			{:else}
				<p class="discret">Aucune candidature.</p>
			{/each}
		</section>
	{/each}
</div>

{#if data.filtres.ecartees}
	<section aria-labelledby="col-ecartees" class="ecartees">
		<h2 id="col-ecartees">Écartées ({data.tableau.ecartees.length})</h2>
		<div class="grille">
			{#each data.tableau.ecartees as carte (`${carte.genre}-${carte.id}`)}
				<CarteSuivi {carte} {suite} erreur={erreurDe(carte.genre, carte.id)} />
			{/each}
		</div>
	</section>
{/if}
