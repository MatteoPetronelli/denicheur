# Proposal

## Why

Le squelette C0 est prêt mais n'a aucun pipeline. Objectif urgent : recevoir chaque jour un digest Telegram en français (et des alertes immédiates) d'offres d'alternance filtrées et notées, sans service payant ni cloud (pivot du 2026-11-16 : Ollama, Planificateur de tâches Windows, SQLite). Voir `docs/plans/2026-11-16-denicheur-roadmap.md` §4 C1.

## What Changes

- **L1** — Modèles pydantic, base SQLite (SQLAlchemy 2 + Alembic, WAL), six tables, dépôt `repo.py`. Alignement sur le pivot local : section `llm:` Ollama, `Secrets` allégé, retrait d'`anthropic` et `psycopg`, `logs/` ignoré.
- **L2** — Client HTTP avec retry/429 et source La bonne alternance (offres + recruteurs).
- **L3** — Normalisation, dédoublonnage, géo (rayon 25 km, lieu à vérifier), préfiltre.
- **L4** — Scoring LLM via Ollama (sortie structurée, cache en base, plafonds d'appels et de durée), script de comparaison de modèles.
- **L5** — API Telegram (envoi seul), messages français, digest ; commandes `setup-telegram` et `digest [--test]`.
- **L6** — `run --mode auto|alternance|stage|digest [--dry-run]`, table `executions`, alertes immédiates, script d'installation de la tâche planifiée Windows.
- **BREAKING** (interne) : les sous-commandes `run` et `init-db` cessent d'être des stubs ; `Secrets` perd `anthropic_api_key`, `telegram_webhook_secret`, `dashboard_password`.

Hors périmètre : bot interactif et boutons (C4), alertes e-mail (C2), Adzuna/stage (C3), brouillons (C5), dashboard (C7). L'envoi d'une candidature reste toujours humain.

## Capabilities

### New Capabilities
- `job-storage`: persistance SQLite des offres, scores, exécutions et paramètres, idempotente, migrations Alembic.
- `lba-source`: collecte des offres et recruteurs de La bonne alternance, avec gestion des erreurs HTTP.
- `offer-filtering`: normalisation, dédoublonnage, filtrage géographique et préfiltre des offres.
- `llm-scoring`: notation des offres par un LLM local Ollama, mise en cache et plafonds.
- `telegram-digest`: messages français et envoi Telegram (digest, alertes), restreint au chat autorisé.
- `daily-run`: orchestration d'une exécution (collecte, scoring, notification), journal, tâche planifiée.

### Modified Capabilities
- `app-config`: la configuration `llm` devient Ollama ; `Secrets` perd les clés cloud.
- `cli-entrypoint`: `run`, `init-db` deviennent fonctionnelles ; `digest` et `setup-telegram` s'ajoutent ; `stats` reste un stub.

## Impact

- Code : `src/denicheur/` (models, db, http, sources, pipeline, scoring, telegram, messages_fr, clock, config, `__main__`), `config/recherches.yaml`, `config/villes_hors_zone.txt`, `migrations/`, `scripts/` (compare_modeles, installer_taches.ps1), tests et fixtures.
- Dépendances : retrait de `anthropic` et `psycopg` ; Ollama local (`qwen2.5:7b-instruct`, à télécharger avant L4).
- Systèmes : Telegram Bot API, API LBA, Ollama (localhost:11434), Planificateur de tâches Windows. Aucun service payant.
