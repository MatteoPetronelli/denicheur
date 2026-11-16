# Dénicheur

Assistant personnel de recherche d'**alternance** (priorité) et de **stage**. Il collecte les offres via des sources officielles, les évalue avec un LLM par rapport au profil du candidat et envoie un digest en français sur Telegram. **L'envoi d'une candidature reste toujours une décision humaine.**

> Statut : squelette en place (CLI, configuration, fixture de test). Le pipeline n'est pas encore écrit.

## Fonctionnement prévu

```text
collecte → dédoublonnage → filtres (distance, mots-clés) → scoring LLM → digest Telegram
```

| Élément | Choix |
|---|---|
| Langage | Python 3.12 (httpx, pydantic, SQLAlchemy, pytest, ruff) |
| Données | SQLite en local, puis Postgres (Neon/Supabase) pour le webhook Telegram |
| LLM | `claude-sonnet-5-5` : effort `low` pour le scoring, `medium` pour la rédaction |
| Exécution | `py -m denicheur run` en local, puis GitHub Actions (cron, UTC) |
| Zone | 25 km autour de Mareil-Marly (78) |

## Sources de données

| Source | Usage | Statut |
|---|---|---|
| La bonne alternance (API) | Offres d'alternance et entreprises pour candidature spontanée | Fonctionne |
| Adzuna | Stages | À tester |
| E-mails d'alerte (Indeed, WTTJ, LinkedIn, JobTeaser) via Gmail | Offres des grands sites, sans scraping | Prévu |
| France Travail (Offres v2, La Bonne Boite v2) | Offres complémentaires | Accès non obtenu |

Aucun scraping de pages protégées, aucun contournement de CAPTCHA, aucun envoi automatique de candidature.

## Configuration

Les secrets se placent uniquement dans un fichier `.env` local (ignoré par git) ou dans les secrets GitHub Actions. Un fichier `.env.example` sans valeurs sera fourni.

| Variable | Rôle |
|---|---|
| `LBA_API_KEY` | Clé de l'API La bonne alternance |
| `ANTHROPIC_API_KEY` | Appels LLM |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Bot Telegram (seul ce `chat_id` est autorisé) |
| `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` | Source stages |
| `DATABASE_URL` | Base de données |
| `FT_CLIENT_ID`, `FT_CLIENT_SECRET` | France Travail, uniquement si l'accès est accordé |

## Test des API

```bash
export LBA_API_KEY="..."   # voir tableau ci-dessus
py test_france_travail.py   # FT_TEST=offres|lbb|entreprises|alternance pour un seul test
```

## Sécurité et vie privée

- Ne jamais committer : `.env`, `identifiants_*.json`, bases de données, `ft_test_results.json`, `CV_base/`, `profile/cv_*.md`.
- Aucune donnée personnelle (téléphone, date de naissance, adresse) n'est envoyée au LLM ni écrite dans les logs.
- Respect des limites des API (La bonne alternance : 60 requêtes/min, usage non lucratif).
- Dépôt à garder **privé**.

## Documentation

- [`Denicheur-specifications.md`](Denicheur-specifications.md) : spécifications complètes.
- [`handoff.md`](handoff.md) : état d'avancement, décisions et prompts de développement.
- [`entreprises_spontanees_mareil-marly.csv`](entreprises_spontanees_mareil-marly.csv) : entreprises IT proches pour candidatures spontanées.
- Workflow de changements : OpenSpec (`openspec/`).

## Installation

```bash
py -m pip install -e ".[dev]"
cp .env.example .env   # puis renseigner les clés ; .env n'est jamais versionné
```

La configuration de recherche est dans `config/recherches.yaml`, le profil envoyé au LLM dans `profile/profil.md` (sans données personnelles).

## Commandes

```bash
py -m denicheur run          # sous-commandes déclarées (run, init-db, stats), pas encore implémentées
py scripts/make_fixture.py   # régénère tests/fixtures/lba_search.json depuis ft_test_results.json
py -m ruff format --check . && py -m ruff check . && py -m mypy src && py -m pytest -q
```
