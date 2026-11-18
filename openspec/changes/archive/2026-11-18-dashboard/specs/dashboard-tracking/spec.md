# Spec Delta

## Purpose

Afficher toutes les candidatures, sur offres et sur entreprises, dans un tableau par statut, et permettre de les modifier avec les mêmes règles que le bot Telegram.

## ADDED Requirements

### Requirement: Kanban by status
La page `/` SHALL présenter une colonne par statut de suivi (`interessante`, `candidature_envoyee`, `relancee`, `entretien`, `offre`, `refus`, `sans_reponse`) et une colonne « Nouvelles » pour les offres notifiées sans suivi. Les candidatures `ignoree` SHALL être masquées par défaut et consultables à la demande. Chaque colonne SHALL afficher son effectif.

#### Scenario: Offer and company together
- **WHEN** une offre et une entreprise sont toutes deux `candidature_envoyee`
- **THEN** les deux cartes sont dans la colonne « Candidature envoyée »

#### Scenario: Ignored hidden
- **WHEN** une candidature est `ignoree`
- **THEN** elle n'apparaît pas dans les colonnes tant que l'utilisateur n'affiche pas les écartées

#### Scenario: Company rows without offer
- **WHEN** une ligne de suivi n'a pas d'offre
- **THEN** elle s'affiche comme entreprise, sans erreur ni offre manquante

### Requirement: Cards
Une carte d'offre SHALL montrer le titre, l'entreprise, le score, la distance et la piste ; une carte d'entreprise SHALL montrer le nom, l'activité, la commune, la distance et la priorité. Chaque carte SHALL renvoyer vers l'offre ou le site de candidature quand le lien existe et commence par `http`.

#### Scenario: Offer card
- **WHEN** une offre notée 82 à 12 km est suivie
- **THEN** sa carte affiche son titre, son entreprise, « 82 » et « 12 km »

#### Scenario: Unsafe link
- **WHEN** le lien d'une entreprise ne commence pas par `http`
- **THEN** la carte n'affiche aucun lien

### Requirement: Status change with bot rules
Un formulaire par carte SHALL proposer uniquement les statuts atteignables depuis le statut courant, selon les mêmes transitions que le bot (nouvelle → `interessante`, `candidature_envoyee` ou `ignoree` ; `interessante` → `candidature_envoyee` ou `ignoree` ; `candidature_envoyee` → `relancee`, issue ou `ignoree` ; `relancee` → issue ou `ignoree` ; issue → `ignoree`). Une transition refusée SHALL laisser la base inchangée.

#### Scenario: Allowed move
- **WHEN** l'utilisateur passe une offre `interessante` à `candidature_envoyee`
- **THEN** le statut change et `envoyee_le` vaut la date du jour

#### Scenario: Refused move
- **WHEN** un formulaire demande de passer une offre `ignoree` à `candidature_envoyee`
- **THEN** une erreur en français s'affiche et le statut reste `ignoree`

#### Scenario: First marking
- **WHEN** une offre « nouvelle » est marquée `interessante`
- **THEN** une seule ligne de suivi est créée pour elle

### Requirement: Same statuses as the bot
La liste des transitions du tableau de bord SHALL être identique à celle du bot ; un test automatique SHALL échouer si les deux listes diffèrent.

#### Scenario: Drift detected
- **WHEN** une transition est ajoutée d'un seul côté
- **THEN** le test de cohérence échoue

### Requirement: Company dates
Marquer une entreprise `candidature_envoyee` SHALL poser sa date de contact et `envoyee_le` ; la marquer `ignoree` SHALL poser sa date d'écart. Marquer à nouveau le même statut SHALL conserver les dates d'origine.

#### Scenario: Contacted
- **WHEN** une entreprise sans suivi est marquée `candidature_envoyee`
- **THEN** sa date de contact et `envoyee_le` valent le jour, en UTC comme les écritures du bot

#### Scenario: Same status again
- **WHEN** le statut courant est redemandé
- **THEN** les dates restent celles d'origine

### Requirement: Companies page
La page `/entreprises` SHALL lister les entreprises avec leur statut de suivi, priorité, distance, effectif, origine, date de contact, lien de candidature, nombre de brouillons et offre ouverte du même SIRET. Elle SHALL filtrer par statut (dont « sans suivi »), par recherche sur le nom et trier par priorité puis distance, par pages de taille fixe.

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

### Requirement: Drafts are read-only
La fiche d'une carte SHALL afficher les brouillons rattachés (type, date, déposé dans Gmail ou non, texte), sans les modifier ni les envoyer.

#### Scenario: Company with drafts
- **WHEN** une entreprise a un brouillon `spontanee` et une `lettre`
- **THEN** les deux apparaissent avec leur texte et leur état Gmail

### Requirement: Offers page
La page `/offres` SHALL lister les offres notées par score décroissant avec leur statut de suivi, y compris celles sous le seuil `score_min` de la configuration, marquées comme telles, et filtrer par piste (stage ou alternance) et par seuil. Les offres rejetées par le préfiltre SHALL en être exclues.

#### Scenario: Below threshold
- **WHEN** une offre notée 40 existe et `score_min` vaut 60
- **THEN** elle figure dans la liste avec la mention « sous le seuil »

#### Scenario: Track filter
- **WHEN** l'utilisateur choisit « stage »
- **THEN** seules les offres de la piste stage s'affichent, partout où le filtre s'applique

### Requirement: Filters on the board
Le tableau SHALL filtrer par piste (stage, alternance) et par nature (offres, entreprises) ; les entreprises n'ont pas de piste et SHALL être traitées comme alternance.

#### Scenario: Stage only
- **WHEN** l'utilisateur choisit « stage »
- **THEN** seules les offres de stage restent affichées et aucune entreprise
