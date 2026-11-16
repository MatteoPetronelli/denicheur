# job-storage Specification

## Purpose
Persister dans un fichier SQLite local les offres, leurs scores LLM, les candidatures, les exécutions et les paramètres, de façon idempotente et partageable entre processus, avec un schéma versionné par migrations.

## Requirements

### Requirement: Versioned schema
Le CLI `init-db` SHALL appliquer les migrations pour créer les six tables `offres`, `scores`, `candidatures`, `brouillons`, `executions` et `parametres`.

#### Scenario: Fresh database
- **WHEN** `init-db` s'exécute sur une base absente
- **THEN** le fichier est créé avec les six tables

#### Scenario: Repeated migration
- **WHEN** `init-db` s'exécute une seconde fois
- **THEN** il se termine sans erreur ni changement de données

### Requirement: Offer uniqueness
Le dépôt SHALL garantir l'unicité d'une offre par `(source, source_id)` et par `url`.

#### Scenario: Same offer inserted twice
- **WHEN** une offre de même `(source, source_id)` est insérée deux fois
- **THEN** la seconde insertion ne crée pas de ligne et retourne l'identifiant existant

### Requirement: Offer and score round trip
Le dépôt SHALL stocker une offre et son score (une ligne de score par offre) et les relire à l'identique.

#### Scenario: Insert and re-read
- **WHEN** une offre et son score sont insérés puis relus
- **THEN** tous les champs relus sont égaux à ceux insérés, y compris les listes `points_forts` et `points_faibles`

### Requirement: Known offers lookup
Le dépôt SHALL fournir l'ensemble des URL et des clés de dédoublonnage déjà connues.

#### Scenario: Known keys
- **WHEN** deux offres sont stockées
- **THEN** leurs URL et clés figurent dans les ensembles retournés

### Requirement: Daily LLM call count
Le dépôt SHALL compter les appels LLM du jour calendaire Europe/Paris.

#### Scenario: Calls on another day
- **WHEN** des scores ont été créés hier à 23:30 Paris et aujourd'hui à 00:10 Paris
- **THEN** seul le second est compté pour aujourd'hui

### Requirement: Key-value parameters
Le dépôt SHALL lire et écrire des paramètres clé-valeur (`pause`, `dernier_digest`, dernières collectes).

#### Scenario: Overwrite
- **WHEN** une clé est écrite deux fois
- **THEN** la lecture retourne la seconde valeur

### Requirement: Concurrent access
Les connexions SQLite SHALL utiliser le mode WAL pour que le run, le bot et le dashboard ne se bloquent pas.

#### Scenario: WAL enabled
- **WHEN** un moteur est créé sur un fichier SQLite
- **THEN** `PRAGMA journal_mode` retourne `wal`
