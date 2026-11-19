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
La page `/stats` SHALL lister les dernières exécutions (date, mode, offres collectées, retenues, notées, notifiées, durée du LLM, erreurs) sans afficher le détail d'une erreur susceptible de contenir un secret. Une exécution avec erreurs SHALL être signalée par un badge distinct de celui des exécutions sans erreur, et les valeurs numériques SHALL être alignées à droite.

#### Scenario: Run with errors
- **WHEN** une exécution a enregistré des erreurs
- **THEN** la ligne indique leur nombre et masque le texte détaillé

#### Scenario: Error badge
- **WHEN** une exécution a 1 erreur et une autre n'en a aucune
- **THEN** la première ligne montre un badge « 1 erreur » de type danger et la seconde « aucune » sans badge danger

### Requirement: Project page
La page `/projet` SHALL présenter en français le but, l'architecture locale et les garde-fous du projet (envoi toujours humain, tout local et gratuit), sans nom, e-mail, téléphone, adresse, chemin de fichier ni donnée issue de la base.

#### Scenario: No personal data
- **WHEN** la page est générée
- **THEN** elle ne contient aucune valeur lue dans la base ni dans le dossier de profil

### Requirement: Offer funnel
La page `/stats` SHALL présenter les étapes vues, retenues, notées et notifiées comme un entonnoir dont chaque barre est proportionnelle au nombre d'offres vues, avec en texte la valeur, la part des offres vues et le taux de passage depuis l'étape précédente. Aucune information SHALL n'être portée par la seule longueur d'une barre.

#### Scenario: Funnel rates
- **WHEN** 40 offres sont vues, 12 retenues, 12 notées et 8 notifiées
- **THEN** l'étape « retenues » indique 12, « 30 % des vues » et « 30 % de l'étape précédente », et l'étape « notifiées » indique 8, « 20 % des vues » et « 67 % de l'étape précédente »

#### Scenario: Empty funnel
- **WHEN** aucune offre n'a été vue
- **THEN** chaque étape indique 0, aucune part ni aucun taux n'affiche « NaN » ou « Infinity », et aucune barre n'est remplie

### Requirement: Status distribution
La page `/stats` SHALL présenter les candidatures par statut, offres et entreprises séparées, par des barres proportionnelles au plus grand effectif, avec leur valeur en texte, sans que la couleur seule distingue offres et entreprises.

#### Scenario: Company count in the distribution
- **WHEN** une entreprise est `interessante` et aucune offre ne l'est
- **THEN** la ligne « Intéressante » indique « Offres 0 » et « Entreprises 1 »
