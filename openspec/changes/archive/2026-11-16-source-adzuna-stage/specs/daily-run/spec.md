# Spec Delta

## MODIFIED Requirements

### Requirement: Due sources
Les sources d'offres d'alternance SHALL être collectées si la dernière collecte date d'au moins 3 h et qu'il est entre 08:00 et 20:00 Paris ; un run tardif rattrape un run manqué. La source e-mail SHALL faire partie des sources collectées lorsque `GMAIL_USER` et `GMAIL_APP_PASSWORD` sont présents, et SHALL être absente sinon. Les sources de stage SHALL être collectées une seule fois par jour Paris, entre 08:00 et 20:00, tant que la date de la dernière collecte de stage n'est pas celle du jour ; `--mode stage` SHALL forcer cette collecte et `--mode alternance` SHALL forcer la seule collecte d'alternance. La source Adzuna SHALL faire partie des sources de stage lorsque `ADZUNA_APP_ID` et `ADZUNA_APP_KEY` sont présents, et SHALL être absente sinon.

#### Scenario: Recent collection
- **WHEN** une collecte d'alternance a eu lieu il y a moins de 3 h
- **THEN** aucune nouvelle collecte d'alternance n'est faite

#### Scenario: Stage collected once a day
- **WHEN** `run --mode auto` tourne à 09:00 Paris et que la dernière collecte de stage date de la veille
- **THEN** les sources de stage sont collectées et la date du jour est enregistrée

#### Scenario: Stage already collected today
- **WHEN** la dernière collecte de stage porte la date du jour Paris
- **THEN** aucune source de stage n'est collectée

#### Scenario: Forced stage mode
- **WHEN** `run --mode stage` tourne hors plage horaire, même si la collecte du jour est faite
- **THEN** les sources de stage sont collectées et celles d'alternance ne le sont pas

#### Scenario: Stage error isolated
- **WHEN** la source Adzuna lève une erreur
- **THEN** l'erreur est consignée sans la clé et la collecte d'alternance de ce run n'est pas affectée

#### Scenario: Email source enabled
- **WHEN** les identifiants Gmail sont présents
- **THEN** la source `email` figure parmi les sources collectées par `run`

#### Scenario: Email source disabled
- **WHEN** `GMAIL_APP_PASSWORD` est absent
- **THEN** `run` ne contient pas la source `email` et ne signale aucune erreur

#### Scenario: Adzuna source disabled
- **WHEN** `ADZUNA_APP_KEY` est absent
- **THEN** `run` ne contient pas de source de stage et ne signale aucune erreur
