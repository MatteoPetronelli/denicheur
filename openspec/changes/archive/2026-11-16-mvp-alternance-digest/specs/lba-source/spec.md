# Spec Delta

## Purpose

Collecter les offres d'alternance et les entreprises recruteuses depuis l'API La bonne alternance et les convertir en offres normalisées, de façon robuste aux limites de débit et aux erreurs réseau.

## ADDED Requirements

### Requirement: HTTP retry policy
Le client HTTP SHALL réessayer sur 429 (en attendant `Retry-After` ou un backoff exponentiel), 5xx et timeout, jusqu'à `max_retries`, et SHALL lever immédiatement sur toute autre erreur 4xx.

#### Scenario: Rate limited then success
- **WHEN** l'API répond 429 avec `Retry-After: 1` puis 200
- **THEN** la requête réussit après une attente de 1 seconde

#### Scenario: Unauthorized
- **WHEN** l'API répond 401
- **THEN** une erreur est levée sans nouvelle tentative

#### Scenario: Server error exhausts retries
- **WHEN** l'API répond 503 à chaque tentative
- **THEN** une erreur est levée après `max_retries` tentatives

### Requirement: LBA offers mapping
La source SHALL interroger l'API LBA autour du centre configuré (rayon et codes ROME de la config) et convertir chaque offre en `Offre` de piste alternance, coordonnées lues en `[lon, lat]`.

#### Scenario: Fixture offers
- **WHEN** la source lit la fixture `lba_search.json`
- **THEN** elle retourne 16 offres

#### Scenario: ITIC mapping
- **WHEN** l'offre ITIC PARIS est convertie
- **THEN** `lat ≈ 48.8579`, `lon ≈ 2.3923`, `debut_des_que_possible` est vrai et `niveau_diplome == "7"`

#### Scenario: Missing company name
- **WHEN** `workplace.name` est nul
- **THEN** l'entreprise est lue dans `legal_name`, puis `brand`, sinon vaut `None`

### Requirement: LBA recruiters
La source SHALL aussi exposer la liste des recruteurs de la réponse pour un usage ultérieur.

#### Scenario: Fixture recruiters
- **WHEN** la source lit la fixture
- **THEN** elle retourne 150 recruteurs

### Requirement: Missing API key
Si `LBA_API_KEY` est absente ou vide, la source SHALL être ignorée avec une ligne de journal, sans faire planter le run.

#### Scenario: No key
- **WHEN** la clé est absente
- **THEN** aucun appel réseau n'est émis et le run continue
