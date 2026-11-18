# Design

## Context

Le bot, le run planifié et le dashboard partagent un seul fichier SQLite (WAL, migrations Alembic 0001–0002 ; voir proposal.md pour la motivation). Le schéma appartient à Python (`src/denicheur/db/tables.py`) ; les règles de statut sont dans `repo._TRANSITIONS` et `repo._marquer`. Les dates sont stockées en UTC sans fuseau, au format SQLAlchemy `YYYY-MM-DD HH:MM:SS.ffffff`. Les suivis d'entreprise ont `offre_id` NULL (piège `NOT IN` déjà traité côté Python). Node 24 et npm 11 sont installés. La roadmap fixe SvelteKit, `better-sqlite3`, `web/`, trois lots (voir `docs/plans/2026-11-16-denicheur-roadmap.md`, C7).

## Goals / Non-Goals

**Goals:**
- Voir et corriger toutes les candidatures (offres et entreprises) dans un navigateur, avec les règles du bot.
- Ne jamais corrompre la base partagée : une seule définition du schéma (Python), une seule liste de transitions.
- Reprendre la prospection : savoir quelles entreprises ont été contactées, écartées, ou n'ont pas de suivi.

**Non-Goals:**
- Pas de migration ni de nouvelle table ; pas d'écriture hors `candidatures` et des dates de `entreprises`.
- Pas de génération de brouillon, de dépôt Gmail, d'envoi, ni de connexion/exposition réseau.
- Pas de démarrage automatique à l'ouverture de session (peut suivre, comme `DenicheurBot`).

## Decisions

- **Adaptateur Node, lancé à la main.** `@sveltejs/adapter-node`, `npm run build` puis `npm start` avec `HOST=127.0.0.1` fixé dans le script. *Alternative écartée :* `vite dev`/`preview` en usage courant (non conçus pour durer, `--host` facile à ouvrir par erreur). Un garde dans `hooks.server.ts` refuse toute requête dont l'en-tête `Host` n'est pas `127.0.0.1` ou `localhost` (rebond DNS).
- **`better-sqlite3`, synchrone, une connexion par processus** (`src/lib/server/db.ts`) : `foreign_keys=ON`, `busy_timeout=5000`, écritures dans `BEGIN IMMEDIATE`. Lecture du schéma jamais créée : si le fichier manque ou si `candidatures` est absente, une erreur claire est renvoyée et rien n'est créé (ouverture en `fileMustExist`). *Repli prévu :* `node:sqlite` intégré à Node 24 si le binaire précompilé de `better-sqlite3` manquait pour cette version de Node.
- **Transitions en un seul fichier de données.** `web/src/lib/transitions.json` (statut courant → statuts permis) importé par `statuts.ts`, lu aussi par un test Python qui le compare à `repo._TRANSITIONS`. *Alternative écartée :* dupliquer dans le TypeScript puis analyser le texte par regex (fragile). La roadmap demande `statuts.ts` : il existe, et réexporte le JSON avec les libellés français.
- **Écriture = port de `_marquer`.** `statuts.ts`/`suivi.ts` reproduisent : erreur si transition refusée, no-op si statut identique, création de la ligne au premier marquage, `envoyee_le` seulement vers `candidature_envoyee`, et pour une entreprise `contactee_le`/`ignoree_le`. Les mêmes jeux de cas passent en Vitest sur une base créée par les migrations Python, ce qui détecte aussi une dérive du format de date. *Décision prise :* le dashboard pose les mêmes dates que le bot (une entreprise « contactée » ici est « contactée » partout).
- **Base de test = vraie base migrée.** Un script `web/tests/creer_base.py` appelle `migrer()` sur un fichier temporaire (`py`), puis Vitest remplit des lignes en SQL. Aucun schéma n'est recopié en TypeScript.
- **Pages et chargement.** `/` charge toutes les lignes de suivi (quelques centaines) et au plus 50 « Nouvelles » récentes ; `/entreprises` et `/offres` sont paginées (50 par page) et filtrées côté SQL, car il y a ~1 200 entreprises. Filtres et pages dans l'URL (`?statut=`, `?q=`, `?page=`), donc partageables et sans JavaScript. Formulaires SvelteKit (`use:enhance`), qui fonctionnent aussi sans JavaScript.
- **Rattachement offre ↔ entreprise par SIRET exact seulement**, comme en C6 (jamais par nom).
- **Seuil de score.** `score_min` lu dans `config/recherches.yaml` (variable `CONFIG_PATH`, paquet `yaml`) pour ne pas copier la valeur ; valeur absente = erreur claire, pas de défaut inventé.
- **Style et accessibilité.** CSS maison sans framework, thème clair/sombre par `prefers-color-scheme`, libellés explicites, contrastes vérifiés avec `fixing-accessibility`. Textes en français ; `/projet` est statique et ne lit rien dans la base.
- **Vérification visuelle** avec `browser-proof` sur une base de démonstration synthétique (jamais la vraie base) pour les captures du README.

## Risks / Trade-offs

- [Trois écrivains (bot, run, dashboard)] → WAL, `busy_timeout`, transactions courtes `BEGIN IMMEDIATE`, message « Base occupée » si l'attente échoue.
- [Dérive des règles de statut entre Python et TypeScript] → un seul JSON de transitions, test Python de cohérence et tests Vitest sur la même base migrée.
- [Format de date divergent → le bot lit mal une date écrite par le dashboard] → test qui écrit en TypeScript puis relit avec les fonctions Python (`repo`).
- [Binaire natif `better-sqlite3` absent pour Node 24 sous Windows] → vérifié dès le lot 1 ; repli `node:sqlite`.
- [Le port 5173/3000 exposé par erreur] → liaison fixée dans le script, garde sur `Host`, avertissement en tête du README.
- [Données personnelles dans les captures] → base synthétique uniquement ; aucune capture de la vraie base.
- [Dépendances npm : surface de supply chain] → peu de paquets, versions épinglées par `package-lock.json`, `npm audit` consulté sans mise à jour automatique.

## Résultats du lot 1

- Mesure du 2026-11-18 : Node 24.14, npm 11.12 ; `better-sqlite3` 13.2.0 s'installe (binaire précompilé) et lit/écrit sous Windows : le repli `node:sqlite` n'est pas nécessaire.
- SvelteKit 3 (généré par `sv` 1.5) : l'alias `$lib` est remplacé par `#lib` (imports avec extension `.js`), et le type `Handle` vient de `@sveltejs/kit/hooks`.
- `npm audit --omit=dev` : 0 vulnérabilité. Les alertes restantes concernent l'outillage de développement (Vite, Vitest), jamais lancé en usage courant ; pas de `npm audit fix --force`.
- Le serveur lancé par `npm start` refuse la connexion depuis l'adresse du réseau local et répond 403 à un `Host` étranger (vérifié par curl et par Playwright).
- Tests de navigateur : `npm run e2e` (Playwright, Chromium) sur une base synthétique créée par Python (`web/.e2e/`, ignorée par git).

## Résultats du lot 2

- Origine du serveur : l'adaptateur Node suppose `https` sans en-tête de protocole ; SvelteKit refusait alors tous les formulaires envoyés en `http` (« Cross-site POST form submissions are forbidden »). `scripts/start.js` fixe `ORIGIN=http://127.0.0.1:<port>` et le garde de `hooks.server.ts` redirige `localhost` vers cette origine (308). Détecté par le test de navigateur, pas par les tests unitaires.
- Les gardes redondantes ont été retirées après mutation (un mutant survivant = code inutile) : l'action de statut laisse `changerStatut` valider le statut, la fiche laisse la requête décider qu'un identifiant illisible n'existe pas.
- Brouillons affichés dans `<pre>` : le texte `<script>` reste du texte (test de navigateur, `window.__xss` jamais posé).
- Tests : 128 Vitest, 27 Playwright (contraste mesuré sur quatre pages en thème clair et sombre, formulaires répétés sans identifiant en double, noms de boutons uniques).

## Résultats du lot 3

- `/stats` : « notifiées » compte les offres envoyées sur Telegram ; les réponses sont les statuts `entretien`, `offre` et `refus` (offres et entreprises comptées séparément puis ensemble) ; la durée du modèle est la moyenne et la somme de `executions.duree_llm_s`. Le texte des erreurs d'une exécution n'est jamais lu ni affiché : seul leur nombre l'est.
- `/projet` ne charge rien (pas de `load`, aucun import de code serveur) ; un test lit le fichier de la page et refuse e-mail, téléphone, chemin de disque, noms de fichiers privés, et un test de navigateur vérifie qu'aucune valeur de la base n'y figure.
- Captures du README : `npm run captures`, base fictive, fichiers dans `docs/captures/`. Pas de capture du bot (messages réels).
- Tests de navigateur : 35 (dont contraste en thème clair et sombre sur sept pages, niveaux de titres, noms de champs, console sans erreur sur toutes les pages).
