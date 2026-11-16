## ADDED Requirements

### Requirement: Bot command
La sous-commande `bot` SHALL lancer la boucle de polling du bot Telegram ; sans `TELEGRAM_BOT_TOKEN` ou sans `TELEGRAM_CHAT_ID`, elle SHALL s'arrêter avec un message en français et le code 1.

#### Scenario: Missing chat id
- **WHEN** `TELEGRAM_CHAT_ID` est absent
- **THEN** la commande affiche un message d'aide, ne contacte pas Telegram et retourne 1
