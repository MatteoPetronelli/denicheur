# Spec Delta

## Purpose

Garder en base locale les entreprises à démarcher sans offre (import du CSV de l'utilisateur, recruteurs de La bonne alternance, recherche d'entreprises publique) et en tirer chaque jour une courte liste jamais répétée, sans aucune donnée personnelle de dirigeant.

## ADDED Requirements

### Requirement: Company record
Une entreprise SHALL être identifiée de façon unique par son SIRET et porter : nom, activité, code NAF, tranche d'effectif, adresse, coordonnées, distance au centre, priorité facultative, lien de candidature spontanée facultatif et origine (CSV, LBA ou recherche d'entreprises). Le nom d'un dirigeant, sa date de naissance et tout autre champ personnel renvoyé par une source ne SHALL jamais être enregistré ni journalisé.

#### Scenario: Same SIRET twice
- **WHEN** deux sources donnent le même SIRET
- **THEN** une seule ligne existe et ses champs descriptifs sont mis à jour

#### Scenario: Directors ignored
- **WHEN** la réponse de la recherche d'entreprises contient des dirigeants
- **THEN** aucun nom ni date de naissance de dirigeant n'est enregistré

### Requirement: CSV import
L'import du CSV de l'utilisateur SHALL lire l'encodage `utf-8-sig` et le séparateur « ; », transformer `rang` en priorité (1 = la plus haute), et créer ou mettre à jour chaque ligne par SIRET. Une ligne sans SIRET ou sans nom SHALL être ignorée et comptée. Un nouvel import SHALL ne jamais effacer l'état de contact, d'écart ou de liste d'une entreprise.

#### Scenario: First import
- **WHEN** le CSV de 150 lignes est importé dans une base vide
- **THEN** 150 entreprises existent avec leur priorité égale au rang et leur lien de candidature spontanée

#### Scenario: Re-import keeps state
- **WHEN** une entreprise écartée est présente dans un second import du même fichier
- **THEN** elle reste écartée et aucune ligne n'est dupliquée

#### Scenario: Coordinates columns
- **WHEN** le CSV porte des colonnes `lat` et `lon`
- **THEN** les coordonnées de chaque entreprise sont enregistrées, et une valeur absente ou illisible reste vide

#### Scenario: Invalid line
- **WHEN** une ligne n'a pas de SIRET
- **THEN** elle est ignorée, comptée dans le bilan, et les autres lignes sont importées

### Requirement: La bonne alternance recruiters
Les recruteurs renvoyés par La bonne alternance SHALL être enregistrés par SIRET s'ils exercent dans l'un des codes NAF configurés, avec leur distance calculée depuis le centre configuré et sans priorité. Une priorité déjà présente SHALL être conservée.

#### Scenario: Recruiter in a configured activity
- **WHEN** un recruteur de NAF 63.11Z est renvoyé
- **THEN** il est enregistré avec sa distance et une priorité vide

#### Scenario: Recruiter outside the activities
- **WHEN** un recruteur d'un autre NAF est renvoyé
- **THEN** il n'est pas enregistré

#### Scenario: Existing priority kept
- **WHEN** un recruteur déjà importé du CSV avec la priorité 4 est renvoyé
- **THEN** sa priorité reste 4

### Requirement: Company search
La recherche d'entreprises SHALL interroger l'API publique sans clé, pour chaque département et chaque code NAF configurés, les unités en activité dont l'effectif est compris entre les bornes configurées, et enregistrer par SIRET l'établissement en activité le plus proche du centre, à condition qu'il soit dans le rayon configuré. Une panne ou une réponse invalide SHALL être consignée sans bloquer le run ni effacer des entreprises déjà enregistrées.

#### Scenario: Nearest active establishment stored
- **WHEN** une unité a un siège éloigné et deux établissements dont un fermé et un actif dans le rayon
- **THEN** l'entreprise est enregistrée avec le SIRET, l'adresse et les coordonnées de l'établissement actif, et sa distance au centre

#### Scenario: Out of range
- **WHEN** aucun établissement actif de l'unité n'est dans le rayon configuré
- **THEN** l'entreprise n'est pas enregistrée

#### Scenario: Size bounds in the request
- **WHEN** la recherche s'exécute avec un effectif minimal de 10 et maximal de 249
- **THEN** la requête ne demande que les tranches d'effectif de 10-19 à 200-249

#### Scenario: API down
- **WHEN** l'API répond par une erreur
- **THEN** l'erreur est consignée, les entreprises déjà en base restent intactes et le run continue

### Requirement: Search progress cursor
Chaque couple département-NAF SHALL avoir un curseur de page mémorisé : une actualisation lit au plus `pages_max` pages à partir du curseur, l'avance de ce nombre de pages et revient à la première page après la dernière. Un échec de requête SHALL laisser le curseur du couple inchangé.

#### Scenario: Cursor advances
- **WHEN** une actualisation lit 3 pages d'un couple dont le curseur vaut 1
- **THEN** le curseur vaut 4 ensuite

#### Scenario: Wraps after the last page
- **WHEN** le curseur atteint une page au-delà de la dernière du couple
- **THEN** la prochaine actualisation recommence à la page 1

#### Scenario: Failure keeps the cursor
- **WHEN** la requête d'un couple échoue
- **THEN** son curseur reste inchangé

### Requirement: One entry per legal unit
Une entreprise dont le SIREN (9 premiers chiffres du SIRET) existe déjà en base SHALL ne pas être créée une seconde fois par la recherche d'entreprises ni par La bonne alternance. Les lignes de l'import CSV font exception : chacune est enregistrée par son SIRET.

#### Scenario: Other establishment of a known company
- **WHEN** l'API renvoie un autre établissement d'une unité déjà importée du CSV
- **THEN** aucune ligne n'est créée et la ligne existante est inchangée

#### Scenario: Unknown company
- **WHEN** le SIREN n'existe pas en base
- **THEN** l'entreprise est créée

### Requirement: Daily list selection
La liste du jour SHALL contenir au plus 10 entreprises jamais listées, jamais contactées et non écartées, triées par priorité croissante (celles sans priorité à la fin), puis par distance croissante, puis par identifiant. Une entreprise SHALL être marquée comme listée dès l'envoi de son message et ne SHALL jamais être listée une seconde fois.

#### Scenario: Order
- **WHEN** trois entreprises ont les priorités 2, 1 et vide
- **THEN** elles sont listées dans l'ordre priorité 1, priorité 2, sans priorité

#### Scenario: Cap of ten
- **WHEN** 40 entreprises sont éligibles
- **THEN** 10 sont listées et 30 restent éligibles pour les jours suivants

#### Scenario: Never twice
- **WHEN** la liste est demandée deux jours de suite sans appui sur un bouton
- **THEN** aucune entreprise n'apparaît dans les deux listes

#### Scenario: Contacted or ignored
- **WHEN** une entreprise est contactée ou écartée
- **THEN** elle n'est plus jamais éligible

### Requirement: Open offers never exclude a company
Une entreprise SHALL rester éligible même si une offre ouverte existe chez elle. Le rapprochement entre une entreprise et des offres SHALL se faire uniquement par SIRET identique, jamais par ressemblance de nom.

#### Scenario: Company with an open offer
- **WHEN** une entreprise éligible a une offre non rejetée portant son SIRET
- **THEN** elle figure dans la liste et son message mentionne cette offre

#### Scenario: Similar name, different SIRET
- **WHEN** une offre porte un nom d'entreprise voisin mais un autre SIRET, ou aucun SIRET
- **THEN** aucune offre n'est rapprochée de l'entreprise
