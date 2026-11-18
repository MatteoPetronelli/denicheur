# Spec Delta

## ADDED Requirements

### Requirement: Company refresh once a day
Une fois par jour Paris, avant la liste du jour, le run SHALL actualiser les entreprises depuis les recruteurs de La bonne alternance et la recherche d'entreprises. Une source en panne SHALL être consignée sans bloquer l'autre, ni la liste, ni le reste du run. Sans clé La bonne alternance, seule la recherche d'entreprises s'exécute.

#### Scenario: Once a day
- **WHEN** `executer` tourne deux fois le même jour
- **THEN** l'actualisation des entreprises n'a lieu qu'une fois

#### Scenario: One source down
- **WHEN** la recherche d'entreprises échoue
- **THEN** les recruteurs LBA sont tout de même enregistrés et l'erreur est consignée dans l'exécution

### Requirement: Daily company list
Une fois par jour, à la suite du digest, le run SHALL envoyer l'en-tête « Entreprises à démarcher » puis la liste du jour, un message par entreprise avec son clavier, et marquer chaque entreprise comme listée dès son envoi. Le paramètre `pause` et l'absence de Telegram SHALL supprimer l'envoi. Sans entreprise éligible, aucun message ne SHALL être envoyé.

#### Scenario: List after the digest
- **WHEN** le digest du jour vient d'être envoyé et 25 entreprises sont éligibles
- **THEN** 10 messages d'entreprise sont envoyés, chacun avec ses boutons

#### Scenario: Twice the same day
- **WHEN** `executer` tourne de nouveau le même jour
- **THEN** aucune seconde liste n'est envoyée

#### Scenario: Interrupted send
- **WHEN** l'envoi échoue au quatrième message
- **THEN** les trois premières entreprises restent listées et ne sont pas renvoyées

#### Scenario: Paused
- **WHEN** le paramètre `pause` vaut `1`
- **THEN** aucune entreprise n'est envoyée ni marquée listée

#### Scenario: Nothing eligible
- **WHEN** toutes les entreprises sont déjà listées, contactées ou écartées
- **THEN** aucun message n'est envoyé
