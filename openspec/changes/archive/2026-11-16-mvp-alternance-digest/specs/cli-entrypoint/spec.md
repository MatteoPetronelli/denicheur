# Spec Delta

## MODIFIED Requirements

### Requirement: Subcommand stubs
Le CLI SHALL déclarer les sous-commandes prévues ; tant qu'une sous-commande n'est pas implémentée, elle SHALL afficher "non implémenté" et ne rien faire d'autre. Les sous-commandes `run`, `init-db`, `digest` et `setup-telegram` SHALL être implémentées ; `stats` reste un stub.

#### Scenario: Stub subcommand
- **WHEN** l'utilisateur lance `py -m denicheur stats`
- **THEN** la sortie contient "non implémenté"

#### Scenario: Implemented subcommand is not a stub
- **WHEN** l'utilisateur lance `py -m denicheur init-db`
- **THEN** la sortie ne contient pas "non implémenté" et la base est migrée

## ADDED Requirements

### Requirement: Run command options
La sous-commande `run` SHALL accepter `--mode` parmi `auto`, `alternance`, `stage`, `digest` (défaut `auto`) et `--dry-run`, et SHALL retourner le code 1 si l'exécution échoue.

#### Scenario: Invalid mode
- **WHEN** l'utilisateur lance `py -m denicheur run --mode inconnu`
- **THEN** le CLI s'arrête avec une erreur d'argument

#### Scenario: Dry run
- **WHEN** l'utilisateur lance `py -m denicheur run --dry-run`
- **THEN** aucun message Telegram n'est envoyé
