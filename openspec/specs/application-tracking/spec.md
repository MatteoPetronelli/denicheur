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
