<svelte:head>
	<title>Le projet · Dénicheur</title>
</svelte:head>

<h1>Le projet Dénicheur</h1>

<p class="intro">
	Dénicheur cherche à ma place des offres d'alternance et de stage en développement, les note avec un modèle de langage
	qui tourne sur mon ordinateur, et m'envoie les meilleures sur Telegram. Il prépare aussi des brouillons de candidature.
	Je relis et j'envoie tout moi-même.
</p>

<h2>Du signal à la candidature</h2>
<ol class="etapes">
	<li>
		<strong>Collecte.</strong> L'API publique La bonne alternance, les alertes Indeed et Jobtome lues en lecture seule dans
		une boîte Gmail, Adzuna pour les stages, et l'annuaire public des entreprises pour les candidatures spontanées.
	</li>
	<li>
		<strong>Filtres.</strong> Doublons, distance, niveau demandé, ancienneté de l'annonce et mots exclus écartent les offres
		hors sujet avant tout appel au modèle.
	</li>
	<li>
		<strong>Notation.</strong> Un modèle exécuté par Ollama sur la machine donne un score de 0 à 100, avec les points forts
		et les points faibles de l'offre par rapport au profil.
	</li>
	<li>
		<strong>Telegram.</strong> Un résumé chaque matin, une alerte immédiate quand une offre dépasse un seuil élevé, et des
		boutons pour garder, écarter ou marquer une candidature comme envoyée.
	</li>
	<li>
		<strong>Brouillons.</strong> E-mail, lettre de motivation en PDF et en DOCX, relance au bout d'une semaine. Le texte est
		déposé dans Gmail comme brouillon : rien ne part sans moi.
	</li>
	<li>
		<strong>Tableau de bord.</strong> Cette application montre toutes les candidatures, offres et entreprises, et permet de
		corriger un statut.
	</li>
</ol>

<h2>Architecture</h2>
<ul>
	<li>Python 3.13, httpx et pydantic pour la collecte et les modèles de données.</li>
	<li>SQLite en mode WAL, avec SQLAlchemy et des migrations Alembic. Le bot, le run planifié et ce tableau partagent le même fichier.</li>
	<li>Le planificateur de tâches de Windows lance le run chaque heure ; le bot Telegram tourne en polling, sans serveur public.</li>
	<li>Ce tableau est une application SvelteKit locale, liée à 127.0.0.1, qui lit la base et écrit par formulaires.</li>
	<li>
		Tests : pytest avec HTTP simulé et faux modèle, Vitest, et Playwright dans un vrai navigateur. Chaque garde est vérifiée
		en la cassant volontairement pour voir le test échouer. Les changements passent par des spécifications OpenSpec.
	</li>
</ul>

<h2>Garde-fous</h2>
<ul>
	<li><strong>L'envoi reste humain.</strong> L'outil écrit des brouillons ; il n'envoie ni candidature, ni message, ni e-mail.</li>
	<li><strong>Tout est local et gratuit.</strong> Aucun service payant ni cloud : le modèle, la base et le tableau tournent sur la même machine.</li>
	<li><strong>Données personnelles chez moi.</strong> CV, coordonnées et clés d'accès restent hors du dépôt et ne sont jamais envoyés au modèle.</li>
	<li><strong>Pas de contournement.</strong> Aucune page protégée n'est lue, aucun CAPTCHA n'est contourné, les limites des API sont respectées.</li>
	<li><strong>Pas de compte, donc pas d'ouverture.</strong> Le tableau n'écoute que sur la machine et refuse tout autre nom d'hôte.</li>
</ul>
