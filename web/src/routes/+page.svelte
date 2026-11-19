<script lang="ts">
	import CarteSuivi from '#lib/components/CarteSuivi.svelte';
	import { COLONNES, GROUPE_STATUT, LIBELLES } from '#lib/statuts.js';
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
	// Indique par un fondu qu'il reste des colonnes à droite, seulement quand c'est vrai.
	function debordement(el: HTMLElement) {
		const maj = () => el.classList.toggle('reste', el.scrollLeft + el.clientWidth < el.scrollWidth - 1);
		const observateur = new ResizeObserver(maj);
		observateur.observe(el);
		el.addEventListener('scroll', maj, { passive: true });
		return {
			destroy() {
				observateur.disconnect();
				el.removeEventListener('scroll', maj);
			}
		};
	}
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
	<button type="submit" class="btn-secondaire">Filtrer</button>
</form>

{#if form && 'ok' in form && form.ok}
	<p role="status" class="ok">
		{#if form.titre && form.statut}« {form.titre} » passée à {LIBELLES[form.statut]}.{:else}Statut mis à jour.{/if}
	</p>
{/if}

<div class="tableau" use:debordement>
	<section class="colonne" class:vide={!data.tableau.nouvelles.length} aria-labelledby="col-nouvelles">
		<h2 id="col-nouvelles"><span class="pastille" aria-hidden="true"></span>Nouvelles <span class="compte">({data.tableau.nouvelles.length})</span></h2>
		{#each data.tableau.nouvelles as carte (`${carte.genre}-${carte.id}`)}
			<CarteSuivi {carte} {suite} scoreMin={data.scoreMin} erreur={erreurDe(carte.genre, carte.id)} />
		{:else}
			<p class="discret">Rien de nouveau.</p>
		{/each}
	</section>
	{#each colonnes as col (col.statut)}
		<section class="colonne" class:vide={!col.cartes.length} aria-labelledby={`col-${col.statut}`}>
			<h2 id={`col-${col.statut}`}>
				<span class={`pastille ${GROUPE_STATUT[col.statut]}`} aria-hidden="true"></span>{LIBELLES[col.statut]} <span class="compte">({col.cartes.length})</span>
			</h2>
			{#each col.cartes as carte (`${carte.genre}-${carte.id}`)}
				<CarteSuivi {carte} {suite} scoreMin={data.scoreMin} erreur={erreurDe(carte.genre, carte.id)} />
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
				<CarteSuivi {carte} {suite} scoreMin={data.scoreMin} erreur={erreurDe(carte.genre, carte.id)} />
			{/each}
		</div>
	</section>
{/if}
