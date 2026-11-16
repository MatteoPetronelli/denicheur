# Spec Delta

## MODIFIED Requirements

### Requirement: Due sources
Les sources d'offres SHALL être collectées si la dernière collecte date d'au moins 3 h et qu'il est entre 08:00 et 20:00 Paris ; un run tardif rattrape un run manqué. La source e-mail SHALL faire partie des sources collectées lorsque `GMAIL_USER` et `GMAIL_APP_PASSWORD` sont présents, et SHALL être absente sinon.

#### Scenario: Recent collection
- **WHEN** une collecte a eu lieu il y a moins de 3 h
- **THEN** aucune nouvelle collecte n'est faite

#### Scenario: Email source enabled
- **WHEN** les identifiants Gmail sont présents
- **THEN** la source `email` figure parmi les sources collectées par `run`

#### Scenario: Email source disabled
- **WHEN** `GMAIL_APP_PASSWORD` est absent
- **THEN** `run` ne contient pas la source `email` et ne signale aucune erreur
