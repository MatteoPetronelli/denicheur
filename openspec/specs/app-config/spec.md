# app-config Specification

## Purpose
Charger et valider la configuration de recherche (`config/recherches.yaml`) et lire les secrets depuis l'environnement, sans jamais les écrire dans git ni les journaux.

## Requirements

### Requirement: Search configuration loading
`load_config(path)` SHALL charger `config/recherches.yaml` en un objet `Config` pydantic validé, dont la section `llm` décrit un LLM local Ollama : URL, appels `scoring` et `ecriture` (modèle, température, `num_ctx`, `timeout_s` chacun), `llm_max_appels_jour` et `llm_max_duree_run_s`.

#### Scenario: Valid file
- **WHEN** `load_config` lit `config/recherches.yaml`
- **THEN** il retourne un `Config` avec `rayon_km == 25` et `niveau_vise == "6"`

#### Scenario: Invalid radius
- **WHEN** le fichier contient `rayon_km: -1`
- **THEN** `load_config` lève une erreur de validation

#### Scenario: Ollama LLM section
- **WHEN** `load_config` lit `config/recherches.yaml`
- **THEN** `llm.fournisseur == "ollama"`, `llm.url == "http://localhost:11434"`, `llm.scoring.modele == "llama3.1:8b"` avec `temperature == 0.0`, `llm.ecriture.temperature == 0.7`, `llm.llm_max_appels_jour == 150` et `llm.llm_max_duree_run_s == 900`

#### Scenario: Legacy cloud fields rejected
- **WHEN** la section `llm` contient un champ de facturation (`llm_budget_mensuel_eur`, `prix_usd_par_mtok`)
- **THEN** `load_config` lève une erreur de validation

### Requirement: Secrets from environment
`load_secrets(env)` SHALL lire les secrets depuis l'environnement ; une clé optionnelle absente ou vide SHALL désactiver la source concernée sans lever d'exception. `Secrets` SHALL NOT contenir de clé de service cloud (`ANTHROPIC_API_KEY`, `TELEGRAM_WEBHOOK_SECRET`, `DASHBOARD_PASSWORD`).

#### Scenario: Adzuna keys missing
- **WHEN** `ADZUNA_APP_ID` et `ADZUNA_APP_KEY` sont absents
- **THEN** `adzuna_enabled` vaut `False`

#### Scenario: Default database
- **WHEN** `DATABASE_URL` est absent ou vide
- **THEN** la valeur par défaut est `sqlite:///denicheur.db`

#### Scenario: Cloud keys ignored
- **WHEN** l'environnement contient `ANTHROPIC_API_KEY`
- **THEN** `Secrets` n'expose aucun attribut `anthropic_api_key`

### Requirement: Profile without PII
`profile/profil.md` SHALL contenir le profil de la spec §2 et ne SHALL contenir ni téléphone, ni e-mail, ni date de naissance, ni adresse.

#### Scenario: PII scan
- **WHEN** un test scanne `profile/profil.md`
- **THEN** aucun motif téléphone, `@` ou "né le" n'est trouvé
