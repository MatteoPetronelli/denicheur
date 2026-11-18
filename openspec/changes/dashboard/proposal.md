# Proposal

## Why

Le suivi tient aujourd'hui dans Telegram (`/candidatures`, boutons) : impossible de voir d'un coup d'œil toutes les
candidatures, d'en corriger une ou de savoir quelles entreprises ont déjà été démarchées. Depuis C6, la base
contient ~1 200 entreprises à démarcher ; l'utilisateur ne commencera pas tant qu'un tableau de bord ne montre pas
qui a été contacté (la liste du jour est désactivée : `entreprises.liste_par_jour: 0`). C7 est le dernier change de
la roadmap et la condition pour reprendre la prospection.

## What Changes

- Nouvelle application locale `web/` (SvelteKit, TypeScript) qui lit et écrit le même fichier SQLite que le bot et
  le run (`DB_PATH`, défaut `../denicheur.db`), liée à `127.0.0.1`, sans connexion ni compte.
- Page `/` : tableau kanban des candidatures par statut, offres **et** entreprises dans les mêmes colonnes ;
  changement de statut par formulaire, avec les mêmes transitions que le bot ; filtres stage/alternance et
  offre/entreprise.
- Page `/offres` : offres notées, dont celles sous le seuil de score, avec leur statut de suivi.
- Page `/entreprises` : liste filtrable des entreprises (statut de suivi, priorité, distance, date de contact,
  lien de candidature, offre ouverte du même SIRET, brouillons rattachés), avec « Contactée » et « Écartée ».
- Page `/stats` : offres vues, retenues, notées, candidatures, réponses, durée LLM (table `executions`).
- Page `/projet` : présentation du projet en français, sans donnée personnelle ; README en français avec captures.
- Les écritures du tableau de bord posent les mêmes dates que le bot (`envoyee_le`, `contactee_le`,
  `ignoree_le`) ; les transitions sont dupliquées en TypeScript et un test Python vérifie qu'elles restent
  identiques à `repo._TRANSITIONS`.
- Hors périmètre : connexion, exposition réseau, génération de brouillons, dépôt Gmail, envoi de candidature
  (toujours humain), nouvelle migration de base.

## Capabilities

### New Capabilities
- `dashboard-app`: application web locale (démarrage, accès à la base, liaison à 127.0.0.1, écritures par formulaire).
- `dashboard-tracking`: kanban des candidatures, statuts partagés avec le bot, filtres, pages offres et entreprises.
- `dashboard-stats`: page de statistiques et page de présentation du projet.

### Modified Capabilities

## Impact

- Nouveau dossier `web/` (SvelteKit, `better-sqlite3`, Vitest) ; `.gitignore` (`web/node_modules`, `web/.svelte-kit`).
- Un test Python lit `web/src/lib/statuts.ts` et le compare à `repo._TRANSITIONS`.
- Node.js 24 est installé ; une nouvelle dépendance npm n'ajoute aucun service payant ni cloud.
- README, CLAUDE.md ; aucune modification du code Python applicatif ni du schéma SQLite (migrations 0001–0002).
- Risque : trois écrivains sur la base (bot, run, dashboard) ; WAL et `busy_timeout` limitent les verrous.
