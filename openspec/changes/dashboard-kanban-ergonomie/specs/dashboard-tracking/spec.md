## MODIFIED Requirements

### Requirement: Kanban by status
La page `/` SHALL présenter une colonne par statut de suivi (`interessante`, `candidature_envoyee`, `relancee`, `entretien`, `offre`, `refus`, `sans_reponse`) et une colonne « Nouvelles » pour les offres notifiées sans suivi. Les candidatures `ignoree` SHALL être masquées par défaut et consultables à la demande. Chaque colonne SHALL afficher son effectif. Toutes les colonnes SHALL être atteignables au clavier et à la souris sans réduire la page ; l'en-tête de chaque colonne SHALL rester visible pendant le défilement vertical, et une colonne vide SHALL occuper moins de largeur qu'une colonne qui contient des cartes.

#### Scenario: Offer and company together
- **WHEN** une offre et une entreprise sont toutes deux `candidature_envoyee`
- **THEN** les deux cartes sont dans la colonne « Candidature envoyée »

#### Scenario: Ignored hidden
- **WHEN** une candidature est `ignoree`
- **THEN** elle n'apparaît pas dans les colonnes tant que l'utilisateur n'affiche pas les écartées

#### Scenario: Company rows without offer
- **WHEN** une ligne de suivi n'a pas d'offre
- **THEN** elle s'affiche comme entreprise, sans erreur ni offre manquante

#### Scenario: Last column reachable
- **WHEN** la fenêtre fait 1280 px de large et qu'une carte est `sans_reponse`
- **THEN** l'utilisateur peut amener la colonne « Sans réponse » à l'écran par défilement ou par tabulation, et la carte reçoit le focus

#### Scenario: Empty column collapsed
- **WHEN** la colonne « Relancée » est vide et que « Nouvelles » contient des cartes
- **THEN** « Relancée » est plus étroite que « Nouvelles » et affiche toujours son libellé et « 0 »

### Requirement: Cards
Une carte d'offre SHALL montrer le titre, l'entreprise, le score, la distance et la piste ; une carte d'entreprise SHALL montrer le nom, l'activité, la commune, la distance et la priorité. Le titre SHALL mener à la fiche de la carte, et toute la surface de la carte SHALL être cliquable vers cette fiche, sans masquer les autres actions de la carte. Chaque carte SHALL renvoyer vers l'offre ou le site de candidature quand le lien existe et commence par `http`. Le score SHALL être signalé comme haut, moyen ou bas par rapport au seuil `score_min`, par du texte et non par la couleur seule.

#### Scenario: Offer card
- **WHEN** une offre notée 82 à 12 km est suivie
- **THEN** sa carte affiche son titre, son entreprise, « 82 » et « 12 km »

#### Scenario: Unsafe link
- **WHEN** le lien d'une entreprise ne commence pas par `http`
- **THEN** la carte n'affiche aucun lien

#### Scenario: Whole card opens the record
- **WHEN** l'utilisateur clique sur la carte hors du titre, du lien externe et du menu de statut
- **THEN** la fiche de la carte s'ouvre

#### Scenario: Score below threshold
- **WHEN** une offre notée 40 est affichée et que `score_min` vaut 65
- **THEN** son badge de score porte un nom accessible qui contient « sous le seuil »

### Requirement: Status change with bot rules
Chaque carte SHALL proposer un menu « Déplacer » qui liste uniquement les statuts atteignables depuis le statut courant, selon les mêmes transitions que le bot (nouvelle → `interessante`, `candidature_envoyee` ou `ignoree` ; `interessante` → `candidature_envoyee` ou `ignoree` ; `candidature_envoyee` → `relancee`, issue ou `ignoree` ; `relancee` → issue ou `ignoree` ; issue → `ignoree`). Chaque action du menu SHALL avoir un nom accessible qui cite la carte et le statut visé, et SHALL fonctionner sans JavaScript. Une transition refusée SHALL laisser la base inchangée. Après un changement réussi, la page SHALL annoncer la carte et son nouveau statut, et le focus SHALL revenir sur la carte déplacée.

#### Scenario: Allowed move
- **WHEN** l'utilisateur passe une offre `interessante` à `candidature_envoyee`
- **THEN** le statut change et `envoyee_le` vaut la date du jour

#### Scenario: Refused move
- **WHEN** un formulaire demande de passer une offre `ignoree` à `candidature_envoyee`
- **THEN** une erreur en français s'affiche et le statut reste `ignoree`

#### Scenario: First marking
- **WHEN** une offre « nouvelle » est marquée `interessante`
- **THEN** une seule ligne de suivi est créée pour elle

#### Scenario: Only reachable statuses
- **WHEN** l'utilisateur ouvre le menu « Déplacer » d'une carte `interessante`
- **THEN** le menu propose « Candidature envoyée » et « Écartée », et rien d'autre

#### Scenario: Announced and focused
- **WHEN** l'utilisateur déplace « Beta SA » vers « Candidature envoyée » au clavier
- **THEN** un message annoncé indique « Beta SA » et « Candidature envoyée », et le focus est sur la carte « Beta SA » dans sa nouvelle colonne

#### Scenario: Move without JavaScript
- **WHEN** JavaScript est désactivé et que l'utilisateur choisit un statut dans le menu
- **THEN** la page se recharge avec la carte dans sa nouvelle colonne
