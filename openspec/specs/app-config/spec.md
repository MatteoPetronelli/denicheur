# app-config Specification

## Purpose
TBD - created by archiving change bootstrap-projet. Update Purpose after archive.

## Requirements

### Requirement: Search configuration loading
`load_config(path)` SHALL charger `config/recherches.yaml` en un objet `Config` pydantic validé.

#### Scenario: Valid file
- **WHEN** `load_config` lit `config/recherches.yaml`
- **THEN** il retourne un `Config` avec `rayon_km == 25` et `niveau_vise == "6"`

#### Scenario: Invalid radius
- **WHEN** le fichier contient `rayon_km: -1`
- **THEN** `load_config` lève une erreur de validation

### Requirement: Secrets from environment
`load_secrets(env)` SHALL lire les secrets depuis l'environnement ; une clé optionnelle absente SHALL désactiver la source concernée sans lever d'exception.

#### Scenario: Adzuna keys missing
- **WHEN** `ADZUNA_APP_ID` et `ADZUNA_APP_KEY` sont absents
- **THEN** `adzuna_enabled` vaut `False`

#### Scenario: Default database
- **WHEN** `DATABASE_URL` est absent
- **THEN** la valeur par défaut est `sqlite:///denicheur.db`

### Requirement: Profile without PII
`profile/profil.md` SHALL contenir le profil de la spec §2 et ne SHALL contenir ni téléphone, ni e-mail, ni date de naissance, ni adresse.

#### Scenario: PII scan
- **WHEN** un test scanne `profile/profil.md`
- **THEN** aucun motif téléphone, `@` ou "né le" n'est trouvé
