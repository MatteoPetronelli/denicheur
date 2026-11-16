# Dénicheur

Assistant personnel de recherche d'**alternance** (priorité) et de **stage**. Il collecte les offres via des sources officielles, les évalue avec un LLM par rapport au profil du candidat et envoie un digest en français sur Telegram. **L'envoi d'une candidature reste toujours une décision humaine.**

> Statut : MVP La bonne alternance en place (collecte, filtres, scoring Ollama, digest et alertes Telegram, tâche planifiée). Alertes e-mail Indeed et Jobtome lues dans Gmail (autres sites : un analyseur par expéditeur dès qu'un e-mail réel existe). Stages collectés via Adzuna (une fois par jour, autour de Marly-le-Roi). Reste à venir : bot interactif, brouillons.

## Fonctionnement

```text
collecte → dédoublonnage → filtres (distance, mots-clés) → scoring LLM → digest Telegram
```

| Élément | Choix |
|---|---|
| Langage | Python 3.13 (httpx, pydantic, SQLAlchemy, pytest, ruff) |
| Données | SQLite locale (`denicheur.db`, migrations Alembic) |
| LLM | Ollama en local, modèle `qwen2.5:14b` (réglages dans `config/recherches.yaml`) |
| Exécution | `py -m denicheur run`, planifié par le Planificateur de tâches Windows |
| Zone | 25 km autour de Mareil-Marly (78) |

## Sources de données

| Source | Usage | Statut |
|---|---|---|
| La bonne alternance (API) | Offres d'alternance et entreprises pour candidature spontanée | Fonctionne |
| Adzuna | Stages (une collecte par jour, `run --mode stage` pour la forcer) | Codé |
| E-mails d'alerte (Indeed, WTTJ, LinkedIn, JobTeaser) via Gmail | Offres des grands sites, sans scraping | Indeed et Jobtome codés ; WTTJ, LinkedIn, JobTeaser à ajouter |
| France Travail (Offres v2, La Bonne Boite v2) | Offres complémentaires | Accès non obtenu |

Aucun scraping de pages protégées, aucun contournement de CAPTCHA, aucun envoi automatique de candidature.

## Configuration

Les secrets se placent uniquement dans un fichier `.env` local, ignoré par git (modèle : `.env.example`).

| Variable | Rôle |
|---|---|
| `LBA_API_KEY` | Clé de l'API La bonne alternance |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Bot Telegram (seul ce `chat_id` est autorisé) |
| `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` | Source stages |
| `DATABASE_URL` | Base de données (défaut `sqlite:///denicheur.db`) |
| `FT_CLIENT_ID`, `FT_CLIENT_SECRET` | France Travail, uniquement si l'accès est accordé |

## Installation et commandes

```bash
py -m pip install -e ".[dev]"
ollama pull qwen2.5:14b
py -m denicheur init-db            # crée denicheur.db
py -m denicheur setup-telegram     # affiche le chat.id à copier dans .env
py -m denicheur digest --test      # envoie une offre factice
py -m denicheur run --mode auto    # collecte, filtre, note, notifie (--dry-run : aucun envoi)
powershell -ExecutionPolicy Bypass -File scripts\installer_taches.ps1   # tâche planifiée « Denicheur »
```

Modes de `run` : `auto` (selon l'heure et l'état en base), `alternance`, `stage`, `digest`. Le paramètre `pause` à `1` en base suspend les envois. Sortie planifiée dans `logs/run.log`.

Contrôles avant commit : `py -m ruff format --check .` · `py -m ruff check .` · `py -m mypy src` · `py -m pytest -q`.

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

## Alertes e-mail (Gmail)

La source e-mail lit le libellé Gmail `Denicheur` en lecture seule (aucun message modifié ni marqué lu). Prérequis : double authentification Google, mot de passe d'application dans `.env` (`GMAIL_USER`, `GMAIL_APP_PASSWORD`), puis un filtre Gmail qui applique le libellé `Denicheur` aux alertes (Indeed et Jobtome pour l'instant). Sans ces deux variables la source est simplement ignorée.
