## ADDED Requirements

### Requirement: Package importable and runnable
Le projet SHALL exposer le paquet `denicheur` (layout `src/`) installable en mode éditable et exécutable via `py -m denicheur`.

#### Scenario: Package imports
- **WHEN** les tests importent `denicheur`
- **THEN** l'import réussit

### Requirement: Subcommand stubs
Le CLI SHALL déclarer les sous-commandes prévues ; tant qu'elles ne sont pas implémentées, chacune SHALL afficher "non implémenté" et ne rien faire d'autre.

#### Scenario: Stub subcommand
- **WHEN** l'utilisateur lance `py -m denicheur run`
- **THEN** la sortie contient "non implémenté"
