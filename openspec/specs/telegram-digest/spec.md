# telegram-digest Specification

## Purpose
Présenter les offres notées à l'utilisateur sous forme de messages Telegram en français, sûrs vis-à-vis du HTML et envoyés uniquement au chat autorisé.

## Requirements

### Requirement: French offer message
Chaque offre SHALL être présentée en un message HTML en français : titre, entreprise, distance « (N km) » ou « 📍 lieu à vérifier », durée et début (« dès que possible » le cas échéant), score, points forts et faibles tronqués à 3 éléments, alerte éventuelle.

#### Scenario: ITIC golden message
- **WHEN** l'offre ITIC notée est formatée
- **THEN** le message égale le texte de référence, avec « (23 km) », « dès que possible » et « ⚠️ Niveau demandé : Bac+5 »

#### Scenario: HTML escaping
- **WHEN** un titre contient `<script>`
- **THEN** le message envoyé contient `&lt;script&gt;`

#### Scenario: Length limit
- **WHEN** un message dépasse 4096 caractères
- **THEN** il est tronqué à cette limite

### Requirement: Daily digest
Le digest SHALL contenir au plus `digest_max_offres` offres de score ≥ `score_min` non encore notifiées, triées par score décroissant, marquer chacune comme notifiée, et envoyer « Rien de nouveau aujourd'hui » s'il n'y en a aucune.

#### Scenario: Top offers
- **WHEN** 12 offres notifiables ont un score ≥ 65
- **THEN** les 10 meilleures sont envoyées par score décroissant et marquées notifiées

#### Scenario: Empty digest
- **WHEN** aucune offre n'est notifiable
- **THEN** un unique message « Rien de nouveau aujourd'hui » est envoyé

### Requirement: Authorized chat only
L'envoi SHALL être lié à `TELEGRAM_CHAT_ID` et SHALL NOT permettre d'écrire à un autre chat.

#### Scenario: Destination
- **WHEN** un message est envoyé
- **THEN** la requête cible le chat configuré

### Requirement: Setup and test commands
`setup-telegram` SHALL afficher le `chat.id` lu dans `getUpdates` ; `digest --test` SHALL envoyer une offre factice.

#### Scenario: Test digest
- **WHEN** l'utilisateur lance `digest --test`
- **THEN** exactement un message d'offre factice est envoyé

### Requirement: Offer keyboard
Chaque message d'offre du digest et des alertes instantanées SHALL porter un clavier en ligne de quatre boutons (« ✅ Je postule », « ✍️ Brouillon », « ⏰ Rappel », « 🚫 Ignorer ») dont chaque donnée identifie l'action et l'offre et tient en 64 octets. Les messages d'en-tête et de test sans offre SHALL ne pas en porter.

#### Scenario: Digest offer has buttons
- **WHEN** un digest envoie une offre
- **THEN** le message porte quatre boutons dont les données désignent l'identifiant de cette offre

#### Scenario: Header has no buttons
- **WHEN** l'en-tête du digest est envoyé
- **THEN** il n'a pas de clavier
