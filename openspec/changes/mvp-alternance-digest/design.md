# Design

## Context

État après C0 : `config.py` (`Config` avec une section `llm` Anthropic, `Secrets` avec clés cloud), CLI à stubs (`run`, `init-db`, `stats`), fixture `tests/fixtures/lba_search.json` (16 offres, 150 recruteurs), `profile/profil.md`. Aucun module métier. Les contrats détaillés sont dans `docs/plans/2026-11-16-denicheur-roadmap.md` (§3.1–3.9) et font foi ; ce document en retient les décisions structurantes. Motivation : voir `proposal.md`.

Contraintes : 100 % local et gratuit (Ollama, SQLite, Planificateur de tâches, Telegram en envoi), tests hors réseau (`httpx.MockTransport`, scoreur factice, `now` injecté), aucune donnée personnelle dans git, prompts ou logs, envoi de candidature toujours humain.

## Goals / Non-Goals

**Goals:**
- Un `py -m denicheur run --mode auto` planifié qui produit digest et alertes en français à partir de LBA.
- Un pipeline idempotent, robuste aux runs manqués et à l'indisponibilité d'Ollama.
- Un modèle de scoring choisi sur mesures (étiquetage humain), pas supposé.

**Non-Goals:**
- Bot interactif, boutons, rappels J+7 (C4) ; e-mails (C2) ; Adzuna/stage (C3) ; brouillons (C5) ; dashboard (C7). Les tables `candidatures` et `brouillons` sont créées mais non utilisées.
- Support PostgreSQL effectif : le code reste compatible, sans le tester.

## Decisions

1. **Découpage en six lots (L1–L6)**, un par session, porte qualité après chacun : `ruff format --check`, `ruff check`, `mypy src`, `pytest -q`. Chaque lot est livrable seul.
2. **SQLAlchemy 2 + Alembic dès L1**, SQLite avec `PRAGMA journal_mode=WAL` posé à la connexion par `make_engine` ; colonnes JSON génériques ; toutes les écritures passent par `db/repo.py`. Alternative écartée : SQL brut (migration future coûteuse).
3. **Une table `scores` = cache LLM** (une ligne par offre, `offre_id` unique). Pas de cache séparé.
4. **Modules et signatures** : `collecter(config, http, now) -> list[Offre]` par source ; `get_json` avec `sleep` injectable ; pipeline en fonctions pures (`normaliser_texte`, `cle_dedup`, `dedupliquer`, `appliquer_geo`, `prefiltrer`) ; `Scorer` en `Protocol` (impl. Ollama + factice) ; `TelegramAPI(token, http)` lié au chat configuré. Tout le texte utilisateur vit dans `messages_fr.py`.
5. **Ollama via httpx** : `POST /api/chat` avec `format = ScoreLLM.model_json_schema()`, `stream=False`, `keep_alive="10m"`, `options` = température, `seed=42`, `num_ctx` depuis la config. Prompt système stable (profil + grille), date dans le message utilisateur pour réutiliser le cache KV. Si le serveur répond 400 sur une option, on la retire et on le note ici. Alternative écartée : SDK `ollama` (dépendance inutile).
6. **Plafonds de scoring** : `llm_max_appels_jour` (appels du jour Paris, tentatives invalides incluses) et `llm_max_duree_run_s`. Connexion refusée = scoring sauté, jamais de crash.
7. **Run orchestré par `executer(mode, deps, now)`** : sources dues selon l'état en base (`parametres`), chacune dans son `try` ; normalisation, dédoublonnage, géo, préfiltre, stockage de *toutes* les nouvelles offres (rejets inclus, motif conservé) ; scoring ; notifications ; clôture de la ligne `executions`. Exception non gérée : message d'échec sans trace, code 1.
8. **Tâche planifiée** par `scripts/installer_taches.ps1` (`Register-ScheduledTask`, utilisateur courant, `-StartWhenAvailable`, `-MultipleInstances IgnoreNew`, limite 30 min, sortie dans `logs/run.log`), idempotent.
9. **Choix du modèle** : `scripts/compare_modeles.py` sur ~20 offres étiquetées par l'utilisateur ; garde le plus petit écart moyen. Si écart moyen > 15 ou plus de 4 offres franchissent 65, arrêt et décision de l'utilisateur.
10. **Alignement pivot dans L1** : `LLMConfig` en `extra="forbid"` pour rejeter les champs de facturation, `Secrets` allégé, `anthropic` et `psycopg` retirés de `pyproject.toml`, `logs/` dans `.gitignore`.

## Risks / Trade-offs

- [Modèle 7B moins fiable qu'un modèle hébergé] → validation par étiquetage humain en L4, seuil d'arrêt explicite, modèle en config.
- [Sortie structurée refusée ou option rejetée par Ollama] → étape bloquante en début de L4 avec appel réel, arrêt et rapport si échec.
- [PC éteint pendant les heures de collecte] → `StartWhenAvailable` et sources « dues » pilotées par l'état : un run tardif rattrape.
- [Collecte LBA : peu d'offres de développement] → attendu (2 retenues sur 16 en fixture) ; C2 ajoute les alertes e-mail.
- [Liste de villes hors zone fixe] → faux positifs possibles, marqué `# shortcut` dans le code ; géocoder les mentions si cela arrive.
- [Données personnelles dans les prompts] → invariant testé (motifs téléphone, `@`, « né le »), prompts bâtis depuis `profil.md` et l'offre seulement.
- [Verrous SQLite entre run et bot futur] → WAL dès L1.

## Migration Plan

Aucune donnée existante. `py -m denicheur init-db` crée `denicheur.db` (ignoré par git) ; retour arrière : supprimer le fichier et désinstaller la tâche (`Unregister-ScheduledTask Denicheur`). Prérequis humains : bot Telegram créé et `TELEGRAM_BOT_TOKEN` renseigné avant L5 ; `ollama pull qwen2.5:14b` avant L4 ; étiquetage de ~20 offres pendant L4.
