# adzuna-source Specification

## Purpose
Collecter les offres de stage proches de Mareil-Marly via l'API Adzuna et les normaliser en `Offre`, sans exposer les clés d'API.

## Requirements

### Requirement: One search per stage keyword
La source SHALL émettre une requête de recherche par mot-clé de `pistes.stage.mots_cles_recherche`, avec `what = "<mot-clé> stage"`, `where` égal à `pistes.stage.lieu_recherche`, `distance` le rayon configuré, `max_days_old` égal à `age_max_jours` et `results_per_page = 50`. Le nombre de requêtes d'une collecte SHALL être égal au nombre de mots-clés et ne SHALL PAS dépasser 10.

#### Scenario: Requests match keywords
- **WHEN** la configuration contient 3 mots-clés
- **THEN** exactement 3 requêtes sont émises, chacune avec son mot-clé suivi de « stage »

#### Scenario: Search place configured
- **WHEN** `pistes.stage.lieu_recherche` vaut « Marly-le-Roi »
- **THEN** chaque requête porte `where=Marly-le-Roi`

#### Scenario: Too many keywords
- **WHEN** la configuration contient plus de 10 mots-clés
- **THEN** le chargement de la configuration échoue

### Requirement: Offer normalization
Chaque résultat SHALL devenir une `Offre` avec `source = "adzuna"`, `source_id = id`, `url = redirect_url` privé de ses paramètres de suivi `utm_*` (qui portent l'App ID), le titre, `company.display_name`, `location.display_name`, les coordonnées `latitude` et `longitude`, `created` converti en UTC avec fuseau (comme la source LBA, le préfiltre le compare à une heure avec fuseau), et la description fournie. Une même offre renvoyée par plusieurs mots-clés SHALL n'apparaître qu'une fois.

#### Scenario: Fixture mapping
- **WHEN** la fixture réelle est normalisée
- **THEN** chaque offre a un `source_id`, une `url` et une description non vides, et aucun `source_id` n'est répété

#### Scenario: App ID kept out of links
- **WHEN** `redirect_url` contient `utm_source=<App ID>`
- **THEN** l'`url` de l'offre ne contient ni ce paramètre ni l'App ID

#### Scenario: Coordinates absent
- **WHEN** un résultat n'a ni `latitude` ni `longitude`
- **THEN** l'offre est conservée avec `lat` et `lon` à `None`

### Requirement: Piste and duration from text
La piste SHALL être `stage` si le titre contient « stage », « stagiaire » ou « internship », sinon `alternance` s'il contient « alternance », « alternant », « apprentissage » ou « apprenti », sinon les mêmes tests sont appliqués à la description, sinon `autre`. La durée en mois SHALL être lue par la forme « N mois » dans le titre puis la description, sinon `None`.

#### Scenario: Stage in title
- **WHEN** le titre est « Stage développeur web (6 mois) »
- **THEN** la piste vaut `stage` et la durée vaut 6

#### Scenario: Alternance in description only
- **WHEN** le titre ne porte aucun mot de piste et la description contient « alternance »
- **THEN** la piste vaut `alternance`

#### Scenario: No signal
- **WHEN** ni le titre ni la description ne portent de mot de piste
- **THEN** la piste vaut `autre`

### Requirement: Remote work flagged
Une offre dont le titre ou la description mentionne le télétravail, le travail hybride ou le remote SHALL avoir `teletravail` à vrai.

#### Scenario: Hybrid offer
- **WHEN** la description contient « poste hybride »
- **THEN** `teletravail` vaut vrai

### Requirement: Credentials never exposed
Les clés `ADZUNA_APP_ID` et `ADZUNA_APP_KEY` SHALL NOT apparaître dans une erreur levée, un journal ou la table `executions`. Une erreur HTTP SHALL être remplacée par une erreur qui ne contient que le code de statut.

#### Scenario: Unauthorized
- **WHEN** l'API répond 401
- **THEN** l'erreur levée ne contient ni la clé ni l'URL de la requête

### Requirement: Source skipped without credentials
Si `ADZUNA_APP_ID` ou `ADZUNA_APP_KEY` est absent ou vide, la source SHALL être absente du run, sans connexion réseau et sans erreur.

#### Scenario: Missing key
- **WHEN** `ADZUNA_APP_KEY` est vide
- **THEN** `run` ne contient pas la source `adzuna` et n'émet aucune requête

### Requirement: Rate limit handling
Une réponse 429 SHALL être réessayée selon la politique HTTP commune ; un échec persistant SHALL être consigné pour cette source sans arrêter le run.

#### Scenario: Persistent 429
- **WHEN** l'API répond 429 à chaque tentative
- **THEN** l'erreur est consignée dans `executions.erreurs` et le reste du run continue
