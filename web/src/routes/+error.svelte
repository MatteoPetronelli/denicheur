<script lang="ts">
	import { page } from '$app/state';
</script>

<svelte:head>
	<title>{page.status === 503 ? 'Base indisponible' : 'Erreur'} · Dénicheur</title>
</svelte:head>

<h1>{page.status === 503 ? 'Base indisponible' : 'Une erreur est survenue'}</h1>
<p class="erreur" role="alert">{page.error?.message}</p>
{#if page.status === 503}
	<p class="discret">
		Vérifie que le fichier existe, ou indique son chemin avec la variable <code>DB_PATH</code>, puis recharge la
		page.
	</p>
{/if}
