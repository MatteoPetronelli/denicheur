## ADDED Requirements

### Requirement: Draft on an untracked offer
Demander un brouillon d'e-mail sur une offre sans suivi SHALL créer d'abord le suivi au statut `interessante`, sans jamais marquer la candidature envoyée. Sur une offre `ignoree` ou à issue finale, la demande SHALL être refusée sans rien créer. Sur une offre déjà suivie à un autre statut permis, le statut SHALL rester inchangé.

#### Scenario: Untracked offer
- **WHEN** un brouillon est demandé pour une offre sans ligne de suivi
- **THEN** la ligne de suivi existe au statut `interessante` et le brouillon lui est rattaché

#### Scenario: Already sent
- **WHEN** un brouillon est demandé pour une offre `candidature_envoyee`
- **THEN** le statut reste `candidature_envoyee`

#### Scenario: Ignored offer
- **WHEN** un brouillon est demandé pour une offre `ignoree`
- **THEN** aucun brouillon ni changement de statut n'est enregistré

### Requirement: One follow-up per application
Une candidature SHALL avoir au plus un brouillon de type `relance`. Générer la relance SHALL marquer la candidature `relancee`. Une relance sur une candidature qui n'est pas `candidature_envoyee` SHALL être refusée.

#### Scenario: First follow-up marks the status
- **WHEN** une relance est enregistrée pour une candidature `candidature_envoyee`
- **THEN** le statut devient `relancee` et un brouillon `relance` existe

#### Scenario: Second follow-up
- **WHEN** une relance existe déjà pour la candidature
- **THEN** la demande est refusée et le nombre de brouillons `relance` reste un

#### Scenario: Not sent yet
- **WHEN** une relance est demandée pour une offre `interessante`
- **THEN** la demande est refusée et le statut ne change pas

### Requirement: Draft storage
Chaque brouillon généré SHALL être enregistré avec son type, son texte complet (ligne de profil et notes comprises), la date de création et l'indicateur « déposé dans Gmail » à faux ; cet indicateur ne SHALL passer à vrai qu'après un dépôt réussi.

#### Scenario: Stored as generated
- **WHEN** un brouillon est généré
- **THEN** il est enregistré avec `gmail_draft` à faux et le texte complet

#### Scenario: Marked after deposit
- **WHEN** le dépôt Gmail réussit
- **THEN** `gmail_draft` vaut vrai
