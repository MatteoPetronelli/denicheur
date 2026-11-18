# Spec Delta

## MODIFIED Requirements

### Requirement: Versioned schema
Le CLI `init-db` SHALL appliquer les migrations pour créer les sept tables `offres`, `scores`, `candidatures`, `brouillons`, `executions`, `parametres` et `entreprises`. La clé `candidatures.entreprise_id` SHALL référencer `entreprises` et être unique : une entreprise a au plus une ligne de suivi. Une offre SHALL pouvoir porter le SIRET facultatif de son employeur.

#### Scenario: Fresh database
- **WHEN** `init-db` s'exécute sur une base absente
- **THEN** le fichier est créé avec les sept tables

#### Scenario: Repeated migration
- **WHEN** `init-db` s'exécute une seconde fois
- **THEN** il se termine sans erreur ni changement de données

#### Scenario: Upgrade keeps data
- **WHEN** `init-db` s'exécute sur une base créée avant l'ajout de `entreprises`, qui contient des offres, des scores et des candidatures
- **THEN** la table `entreprises` est ajoutée et toutes les lignes existantes sont conservées

#### Scenario: Offer SIRET round trip
- **WHEN** une offre portant un SIRET est insérée puis relue, et une autre sans SIRET aussi
- **THEN** la première retrouve son SIRET et la seconde a un SIRET vide

#### Scenario: One tracking line per company
- **WHEN** deux lignes de suivi portent le même `entreprise_id`
- **THEN** la seconde insertion est refusée
