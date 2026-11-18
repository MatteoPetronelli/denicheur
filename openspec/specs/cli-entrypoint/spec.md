# cli-entrypoint Specification

## Purpose
Exposer le point d'entrée `py -m denicheur` et ses sous-commandes (`run`, `init-db`, `digest`, `setup-telegram`, `stats`).

## Requirements

### Requirement: Package importable and runnable
Le projet SHALL exposer le paquet `denicheur` (layout `src/`) installable en mode éditable et exécutable via `py -m denicheur`.

#### Scenario: Package imports
- **WHEN** les tests importent `denicheur`
- **THEN** l'import réussit

### Requirement: Subcommand stubs
Le CLI SHALL déclarer les sous-commandes prévues ; tant qu'une sous-commande n'est pas implémentée, elle SHALL afficher "non implémenté" et ne rien faire d'autre. Les sous-commandes `run`, `init-db`, `digest` et `setup-telegram` SHALL être implémentées ; `stats` reste un stub.

#### Scenario: Stub subcommand
- **WHEN** l'utilisateur lance `py -m denicheur stats`
- **THEN** la sortie contient "non implémenté"

#### Scenario: Implemented subcommand is not a stub
- **WHEN** l'utilisateur lance `py -m denicheur init-db`
- **THEN** la sortie ne contient pas "non implémenté" et la base est migrée

### Requirement: Run command options
La sous-commande `run` SHALL accepter `--mode` parmi `auto`, `alternance`, `stage`, `digest` (défaut `auto`) et `--dry-run`, et SHALL retourner le code 1 si l'exécution échoue.

#### Scenario: Invalid mode
- **WHEN** l'utilisateur lance `py -m denicheur run --mode inconnu`
- **THEN** le CLI s'arrête avec une erreur d'argument

#### Scenario: Dry run
- **WHEN** l'utilisateur lance `py -m denicheur run --dry-run`
- **THEN** aucun message Telegram n'est envoyé

### Requirement: Bot command
La sous-commande `bot` SHALL lancer la boucle de polling du bot Telegram ; sans `TELEGRAM_BOT_TOKEN` ou sans `TELEGRAM_CHAT_ID`, elle SHALL s'arrêter avec un message en français et le code 1.

#### Scenario: Missing chat id
- **WHEN** `TELEGRAM_CHAT_ID` est absent
- **THEN** la commande affiche un message d'aide, ne contacte pas Telegram et retourne 1

### Requirement: Company import command
La sous-commande `import-entreprises <fichier>` SHALL importer le CSV indiqué dans la base et afficher en français le nombre d'entreprises créées, mises à jour et ignorées. Un fichier absent ou illisible SHALL donner un message en français sans trace d'erreur et le code 1.

#### Scenario: Import
- **WHEN** l'utilisateur lance `py -m denicheur import-entreprises data/entreprises_spontanees_mareil-marly.csv`
- **THEN** la sortie indique les nombres créées, mises à jour et ignorées, et le code de sortie est 0

#### Scenario: Missing file
- **WHEN** le fichier n'existe pas
- **THEN** un message en français s'affiche, sans trace d'erreur, et le code de sortie est 1
