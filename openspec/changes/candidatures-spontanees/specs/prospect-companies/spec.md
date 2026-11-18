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
La recherche d'entreprises SHALL interroger l'API publique sans clé, pour chaque code NAF configuré, dans le rayon configuré autour du centre, pour les établissements en activité de moins de 250 salariés, et enregistrer le résultat par SIRET. Une panne ou une réponse invalide SHALL être consignée sans bloquer le run ni effacer des entreprises déjà enregistrées.

#### Scenario: Results stored
- **WHEN** l'API renvoie des entreprises actives de NAF 62.01Z
- **THEN** elles sont enregistrées avec leur distance au centre et l'origine « recherche d'entreprises »

#### Scenario: Large company excluded
- **WHEN** une entreprise a 500 salariés ou plus
- **THEN** elle n'est pas enregistrée

#### Scenario: API down
- **WHEN** l'API répond par une erreur
- **THEN** l'erreur est consignée, les entreprises déjà en base restent intactes et le run continue

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
