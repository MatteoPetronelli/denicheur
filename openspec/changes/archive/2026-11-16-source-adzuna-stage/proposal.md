# Proposal

## Why

La piste stage n'a aucune source : La bonne alternance ne couvre que l'alternance et les alertes e-mail dépendent de ce que reçoit la boîte. Adzuna est un agrégateur gratuit (App ID/Key déjà dans `.env`) qui couvre les stages autour de Mareil-Marly. C3 apporte les offres de stage au pipeline existant.

## What Changes

- Nouvelle source `adzuna` (`sources/adzuna.py`) : une requête par mot-clé de stage, normalisation vers `Offre`, piste déduite du titre puis de la description, durée lue dans le texte, aucune clé dans les erreurs.
- Nouveaux réglages `pistes.stage.mots_cles_recherche` et `pistes.stage.lieu_recherche` (Adzuna ne connaît pas Mareil-Marly ; « Marly-le-Roi » fonctionne) dans `config/recherches.yaml` (au plus 10 requêtes par jour).
- `run` collecte les sources de stage une fois par jour (date Paris), séparément du rythme de 3 h de l'alternance ; `--mode stage` force cette collecte.
- Branchement dans `__main__._run` seulement si `ADZUNA_APP_ID` et `ADZUNA_APP_KEY` existent.
- Fixture réelle `tests/fixtures/adzuna_search.json`.

Hors périmètre : suivi des liens ou récupération de la description complète, nouvelle règle de préfiltre sur la durée ou la date de début (le scoring les juge), France Travail, boutons Telegram (C4).

## Capabilities

### New Capabilities
- `adzuna-source`: collecte des offres de stage via l'API Adzuna et normalisation vers `Offre`.

### Modified Capabilities
- `daily-run`: la collecte des sources de stage est due une fois par jour Paris et peut être forcée par `--mode stage`.

## Impact

- Code : `sources/adzuna.py`, `sources/texte.py`, `config.py` (`PisteStage`), `pipeline/run.py` (`Deps.sources_stage`, échéance stage), `__main__.py`.
- Config : `config/recherches.yaml`. Secrets : `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` (déjà modélisés dans `Secrets`).
- Réseau : `api.adzuna.com`, au plus 10 appels par jour. Aucune dépendance nouvelle.
