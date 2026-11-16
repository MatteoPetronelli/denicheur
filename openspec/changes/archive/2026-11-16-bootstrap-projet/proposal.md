# Proposal

## Why

Le dépôt ne contient que des documents : aucun paquet Python, aucune config, aucune fixture. Avant d'écrire le pipeline (C1), il faut un squelette exécutable et testé, la configuration validée, le profil sans PII et la fixture LBA réelle utilisée par tous les tests hors-ligne.

## What Changes

- Lot 1 : `pyproject.toml` (src layout, deps, ruff/pytest), paquet `src/denicheur` avec CLI `py -m denicheur` (sous-commandes stubs), `.env.example`, test de fumée, `.gitignore` complété.
- Lot 2 : `config/recherches.yaml`, `config.py` (`load_config`, `load_secrets`), `profile/profil.md` (spec §2, sans contacts), `scripts/make_fixture.py` + `tests/fixtures/lba_search.json` committée, README FR.
- Aucune logique métier (collecte, scoring, Telegram) : hors périmètre, voir C1.

## Capabilities

### New Capabilities
- `cli-entrypoint`: point d'entrée `py -m denicheur` avec sous-commandes déclarées mais non implémentées.
- `app-config`: chargement validé de `config/recherches.yaml` et des secrets depuis l'environnement, sources désactivées si clé absente.
- `lba-fixture`: fixture LBA reproductible (16 offres, 150 recruteurs) générée par script depuis `ft_test_results.json`.

### Modified Capabilities

## Impact

- Nouveaux fichiers : `pyproject.toml`, `.env.example`, `src/denicheur/`, `tests/`, `config/`, `profile/profil.md`, `scripts/`, README.
- Dépendances : httpx, pydantic, SQLAlchemy, Alembic, psycopg, anthropic, PyYAML, python-dotenv, tzdata ; dev : pytest, ruff, mypy.
- `ft_test_results.json`, `CV_base/` et `.env` restent hors git.
