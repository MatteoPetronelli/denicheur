## ADDED Requirements

### Requirement: List values presentation
Sur `/entreprises` et `/offres`, une valeur absente SHALL s'afficher « — », les valeurs numériques SHALL être alignées à droite, et la mention « sous le seuil » SHALL être un badge distinct du score.

#### Scenario: Missing value
- **WHEN** une entreprise n'a ni activité ni effectif
- **THEN** ces deux valeurs s'affichent « — »

#### Scenario: Threshold badge apart from the score
- **WHEN** une offre notée 40 est sous le seuil
- **THEN** « 40 » et « sous le seuil » sont deux éléments distincts de la même cellule

### Requirement: Numbered pagination
La navigation entre pages de `/entreprises` et `/offres` SHALL proposer la première page, la dernière et les pages voisines de la page courante, marquer la page courante et signaler les pages omises.

#### Scenario: Numbered pages
- **WHEN** le filtre donne 24 pages et que l'utilisateur est en page 10
- **THEN** la navigation propose les pages 1, 9, 10, 11 et 24, marque la page 10 comme courante et signale les pages omises

### Requirement: Lists on small screens
Sous 48rem de large, chaque entreprise de `/entreprises` et chaque offre de `/offres` SHALL s'afficher comme un bloc où chaque valeur porte son libellé, sans défilement horizontal du document.

#### Scenario: Narrow screen
- **WHEN** `/entreprises` ou `/offres` est affichée à 375 px de large
- **THEN** chaque ligne est un bloc lisible avec ses libellés, et le document ne défile pas horizontalement

### Requirement: Record page navigation
La fiche d'une offre ou d'une entreprise SHALL indiquer par un fil d'Ariane la liste dont elle relève (`/offres` ou `/entreprises`) et y renvoyer, SHALL présenter son statut de suivi comme un badge accompagné de son libellé, et le texte d'un brouillon SHALL garder ses retours à la ligne sans défilement horizontal.

#### Scenario: Breadcrumb
- **WHEN** l'utilisateur ouvre la fiche de l'entreprise « Beta SA »
- **THEN** un fil d'Ariane « Entreprises › Beta SA » mène à `/entreprises`, et la page courante y est marquée comme telle

#### Scenario: Long draft line
- **WHEN** un brouillon contient une ligne de 300 caractères sans retour
- **THEN** la ligne passe à la ligne dans la carte du brouillon, sans défilement horizontal
