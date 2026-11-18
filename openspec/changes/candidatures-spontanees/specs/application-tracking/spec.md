# Spec Delta

## ADDED Requirements

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
