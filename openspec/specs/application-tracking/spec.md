# application-tracking Specification

## Purpose
Suivre l'avancement de chaque candidature (statuts, transitions valides, relances dues, statistiques) dans la base locale, sans jamais envoyer de candidature à la place de l'utilisateur.

## Requirements

### Requirement: Application statuses
Une offre SHALL pouvoir porter un des statuts `interessante`, `candidature_envoyee`, `relancee`, `entretien`, `refus`, `offre`, `sans_reponse`, `ignoree` ; une offre sans suivi est « nouvelle ». Le suivi SHALL être consigné dans `candidatures`, au plus une ligne par offre.

#### Scenario: First marking creates the tracking row
- **WHEN** une offre sans suivi est marquée `candidature_envoyee`
- **THEN** une ligne `candidatures` existe pour cette offre avec ce statut et `envoyee_le` égal à la date du jour

#### Scenario: One row per offer
- **WHEN** la même offre est marquée deux fois avec des statuts différents
- **THEN** une seule ligne `candidatures` existe pour elle

### Requirement: Valid transitions only
Les transitions autorisées SHALL être : nouvelle → `interessante` ou `candidature_envoyee` ; `interessante` → `candidature_envoyee` ; `candidature_envoyee` → `relancee`, `entretien`, `refus`, `offre` ou `sans_reponse` ; `relancee` → `entretien`, `refus`, `offre` ou `sans_reponse` ; tout statut → `ignoree`. Toute autre transition SHALL être refusée par une erreur et SHALL laisser la base inchangée.

#### Scenario: Refused transition
- **WHEN** une offre `ignoree` est marquée `candidature_envoyee`
- **THEN** une erreur de transition est levée et le statut reste `ignoree`

#### Scenario: Ignore from anywhere
- **WHEN** une offre `entretien` est marquée `ignoree`
- **THEN** son statut devient `ignoree`

#### Scenario: Same status again
- **WHEN** une offre `candidature_envoyee` est de nouveau marquée `candidature_envoyee`
- **THEN** la date `envoyee_le` d'origine est conservée

### Requirement: Unknown offer
Marquer une offre inexistante SHALL lever une erreur sans rien écrire.

#### Scenario: Missing offer
- **WHEN** l'identifiant d'offre n'existe pas
- **THEN** une erreur est levée et aucune ligne `candidatures` n'est créée

### Requirement: Applications due for a reminder
Les candidatures à relancer SHALL être celles de statut `candidature_envoyee` dont `envoyee_le` date d'au moins 7 jours et dont `rappel_le` est vide.

#### Scenario: Seven days
- **WHEN** une candidature est envoyée depuis 7 jours, et une autre depuis 6 jours
- **THEN** seule la première est à relancer

#### Scenario: Already reminded
- **WHEN** `rappel_le` est renseigné
- **THEN** la candidature n'est plus à relancer

### Requirement: Statistics
Les statistiques SHALL donner le nombre d'offres par statut de suivi, le nombre d'offres nouvelles notifiées sans suivi, et le nombre d'offres rejetées par le préfiltre.

#### Scenario: Counts
- **WHEN** 2 offres sont `candidature_envoyee`, 1 `ignoree` et 3 notifiées sans suivi
- **THEN** les statistiques indiquent 2, 1 et 3 pour ces catégories

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

### Requirement: Company tracking
Une entreprise SHALL pouvoir être suivie comme une offre, avec les mêmes statuts et les mêmes transitions, par une ligne de suivi unique rattachée à l'entreprise et sans offre. « Envoyée » SHALL marquer la candidature envoyée et poser la date de contact de l'entreprise. « Ignorer » SHALL écarter l'entreprise. Une entreprise inconnue SHALL être refusée sans rien créer.

#### Scenario: Marked as sent
- **WHEN** l'utilisateur marque une entreprise sans suivi comme envoyée
- **THEN** la ligne de suivi est `candidature_envoyee`, `envoyee_le` et la date de contact de l'entreprise valent le jour

#### Scenario: Ignored company
- **WHEN** une entreprise est écartée
- **THEN** elle est marquée écartée et ne peut plus recevoir de brouillon

#### Scenario: Unknown company
- **WHEN** l'identifiant d'entreprise n'existe pas
- **THEN** la demande est refusée et aucune ligne n'est créée

### Requirement: Draft on a company
Un brouillon `spontanee` ou `lettre` sur une entreprise sans suivi SHALL créer d'abord le suivi `interessante`, sans jamais marquer la candidature envoyée. Il SHALL être refusé sur une entreprise écartée, contactée ou à issue finale. Une entreprise SHALL ne jamais recevoir de brouillon `relance`.

#### Scenario: Untracked company
- **WHEN** un brouillon est demandé pour une entreprise sans suivi
- **THEN** le suivi existe au statut `interessante` et le brouillon lui est rattaché

#### Scenario: Contacted company
- **WHEN** un brouillon est demandé pour une entreprise déjà contactée
- **THEN** aucun brouillon n'est enregistré

#### Scenario: Follow-up on a company
- **WHEN** une relance est demandée pour une entreprise
- **THEN** la demande est refusée et aucun brouillon n'est enregistré

### Requirement: Daily cap on company drafts
Au plus 15 brouillons d'entreprise SHALL être enregistrés par jour Paris. Au-delà, la demande SHALL être refusée avant tout appel au modèle, avec un message en français.

#### Scenario: Sixteenth draft of the day
- **WHEN** 15 brouillons d'entreprise existent déjà aujourd'hui et un seizième est demandé
- **THEN** il est refusé, le modèle n'est pas appelé et aucun brouillon n'est enregistré

#### Scenario: Next day
- **WHEN** le jour Paris suivant commence
- **THEN** un nouveau brouillon d'entreprise est accepté

#### Scenario: Offer drafts not counted
- **WHEN** 15 brouillons d'offres existent aujourd'hui
- **THEN** un brouillon d'entreprise est accepté
