# dashboard-stats Specification

## Purpose
Donner une vue chiffrée du fonctionnement du Dénicheur et une page de présentation du projet, sans donnée personnelle, utilisable dans un portfolio.

## Requirements

### Requirement: Statistics page
La page `/stats` SHALL afficher le nombre d'offres vues, retenues par le préfiltre, notées, notifiées, de candidatures par statut (offres et entreprises séparées), de réponses (`entretien`, `offre`, `refus`) et la durée moyenne et totale du LLM tirée de l'historique des exécutions. Un chiffre sans donnée SHALL s'afficher à zéro, jamais en erreur.

#### Scenario: Counts
- **WHEN** la base contient 10 offres dont 4 rejetées, 5 notées, 2 candidatures envoyées et 1 refus
- **THEN** la page indique 10 vues, 6 retenues, 5 notées, 2 envoyées et 1 réponse

#### Scenario: Empty database
- **WHEN** la base ne contient aucune exécution
- **THEN** la durée du LLM s'affiche « 0 s » sans erreur

#### Scenario: Company applications
- **WHEN** 3 entreprises sont `candidature_envoyee`
- **THEN** elles sont comptées dans la ligne des entreprises, pas dans celle des offres

### Requirement: Recent runs
La page `/stats` SHALL lister les dernières exécutions (date, mode, offres collectées, retenues, notées, notifiées, durée du LLM, erreurs) sans afficher le détail d'une erreur susceptible de contenir un secret.

#### Scenario: Run with errors
- **WHEN** une exécution a enregistré des erreurs
- **THEN** la ligne indique leur nombre et masque le texte détaillé

### Requirement: Project page
La page `/projet` SHALL présenter en français le but, l'architecture locale et les garde-fous du projet (envoi toujours humain, tout local et gratuit), sans nom, e-mail, téléphone, adresse, chemin de fichier ni donnée issue de la base.

#### Scenario: No personal data
- **WHEN** la page est générée
- **THEN** elle ne contient aucune valeur lue dans la base ni dans le dossier de profil
