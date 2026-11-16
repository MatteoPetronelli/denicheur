## ADDED Requirements

### Requirement: J+7 reminders
Le run SHALL envoyer, entre 08:00 et 20:00 Paris, un message de rappel en français pour chaque candidature à relancer (envoyée depuis au moins 7 jours, jamais rappelée), puis renseigner `rappel_le` ; un rappel ne SHALL être envoyé qu'une fois. Le paramètre `pause` à `1` SHALL supprimer l'envoi sans renseigner `rappel_le`.

#### Scenario: Reminder at day 7
- **WHEN** une candidature a été envoyée il y a 7 jours
- **THEN** un rappel est envoyé et `rappel_le` est renseigné

#### Scenario: Not at day 6
- **WHEN** une candidature a été envoyée il y a 6 jours
- **THEN** aucun rappel n'est envoyé

#### Scenario: Not twice
- **WHEN** le run tourne de nouveau après le rappel
- **THEN** aucun second rappel n'est envoyé

#### Scenario: Paused
- **WHEN** `pause` vaut `1` et qu'une candidature est due
- **THEN** aucun rappel n'est envoyé et la candidature reste due
