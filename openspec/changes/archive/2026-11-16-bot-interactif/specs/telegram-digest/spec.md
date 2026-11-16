## ADDED Requirements

### Requirement: Offer keyboard
Chaque message d'offre du digest et des alertes instantanées SHALL porter un clavier en ligne de quatre boutons (« ✅ Je postule », « ✍️ Brouillon », « ⏰ Rappel », « 🚫 Ignorer ») dont chaque donnée identifie l'action et l'offre et tient en 64 octets. Les messages d'en-tête et de test sans offre SHALL ne pas en porter.

#### Scenario: Digest offer has buttons
- **WHEN** un digest envoie une offre
- **THEN** le message porte quatre boutons dont les données désignent l'identifiant de cette offre

#### Scenario: Header has no buttons
- **WHEN** l'en-tête du digest est envoyé
- **THEN** il n'a pas de clavier
