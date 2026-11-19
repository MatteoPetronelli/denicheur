## MODIFIED Requirements

### Requirement: Companies page
La page `/entreprises` SHALL lister les entreprises avec leur statut de suivi, priorité, distance, effectif, origine, date de contact, lien de candidature, nombre de brouillons et offre ouverte du même SIRET. Elle SHALL filtrer par statut (dont « sans suivi »), par recherche sur le nom et trier par priorité puis distance, par pages de taille fixe. Une valeur absente SHALL s'afficher « — », les valeurs numériques SHALL être alignées à droite, et la navigation entre pages SHALL proposer la première page, la dernière et les pages voisines de la page courante. Sous 48rem de large, chaque entreprise SHALL s'afficher comme un bloc où chaque valeur porte son libellé, sans défilement horizontal.

#### Scenario: Not yet contacted
- **WHEN** l'utilisateur filtre « sans suivi »
- **THEN** seules les entreprises sans ligne de suivi s'affichent, priorité d'abord, puis distance

#### Scenario: Open offer by SIRET
- **WHEN** une offre porte le même SIRET qu'une entreprise
- **THEN** la ligne de l'entreprise montre le titre de cette offre

#### Scenario: Name sharing without SIRET
- **WHEN** une offre porte le même nom d'entreprise mais aucun SIRET identique
- **THEN** aucune offre n'est rattachée à l'entreprise

#### Scenario: Large list
- **WHEN** plus d'une page d'entreprises correspond au filtre
- **THEN** seule la page demandée est chargée et la navigation entre pages est proposée

#### Scenario: Numbered pages
- **WHEN** le filtre donne 24 pages et que l'utilisateur est en page 10
- **THEN** la navigation propose les pages 1, 9, 10, 11 et 24, marque la page 10 comme courante et signale les pages omises

#### Scenario: Missing value
- **WHEN** une entreprise n'a ni activité ni effectif
- **THEN** ces deux valeurs s'affichent « — »

#### Scenario: Narrow screen
- **WHEN** la page est affichée à 375 px de large
- **THEN** chaque entreprise est un bloc lisible avec ses libellés, et le document ne défile pas horizontalement

### Requirement: Drafts are read-only
La fiche d'une carte SHALL afficher les brouillons rattachés (type, date, déposé dans Gmail ou non, texte), sans les modifier ni les envoyer. Le texte d'un brouillon SHALL garder ses retours à la ligne et rester lisible sans défilement horizontal.

#### Scenario: Company with drafts
- **WHEN** une entreprise a un brouillon `spontanee` et une `lettre`
- **THEN** les deux apparaissent avec leur texte et leur état Gmail

#### Scenario: Long draft line
- **WHEN** un brouillon contient une ligne de 300 caractères sans retour
- **THEN** la ligne passe à la ligne dans la carte du brouillon, sans défilement horizontal

### Requirement: Offers page
La page `/offres` SHALL lister les offres notées par score décroissant avec leur statut de suivi, y compris celles sous le seuil `score_min` de la configuration, marquées comme telles, et filtrer par piste (stage ou alternance) et par seuil. Les offres rejetées par le préfiltre SHALL en être exclues. Le score et la distance SHALL être alignés à droite, et la mention « sous le seuil » SHALL être un badge distinct du score. Sous 48rem de large, chaque offre SHALL s'afficher comme un bloc libellé, sans défilement horizontal.

#### Scenario: Below threshold
- **WHEN** une offre notée 40 existe et `score_min` vaut 60
- **THEN** elle figure dans la liste avec la mention « sous le seuil »

#### Scenario: Track filter
- **WHEN** l'utilisateur choisit « stage »
- **THEN** seules les offres de la piste stage s'affichent, partout où le filtre s'applique

#### Scenario: Narrow screen offers
- **WHEN** la page est affichée à 375 px de large
- **THEN** chaque offre est un bloc lisible avec ses libellés, et le document ne défile pas horizontalement

## ADDED Requirements

### Requirement: Record page navigation
La fiche d'une offre ou d'une entreprise SHALL indiquer par un fil d'Ariane la liste dont elle relève (`/offres` ou `/entreprises`) et y renvoyer, et SHALL présenter son statut de suivi comme un badge accompagné de son libellé.

#### Scenario: Breadcrumb
- **WHEN** l'utilisateur ouvre la fiche de l'entreprise « Beta SA »
- **THEN** un fil d'Ariane « Entreprises › Beta SA » mène à `/entreprises`, et la page courante y est marquée comme telle
