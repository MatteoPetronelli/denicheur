# dashboard-app Specification

## Purpose
Fournir une application web locale qui lit et modifie la base SQLite du Dénicheur, sans compte ni exposition réseau, pour consulter et corriger le suivi des candidatures depuis un navigateur.

## Requirements

### Requirement: Local-only access
L'application SHALL n'écouter que sur l'interface locale `127.0.0.1` et SHALL ne demander ni connexion ni mot de passe. Aucune commande de démarrage documentée SHALL l'exposer sur une autre interface.

#### Scenario: Default start
- **WHEN** l'utilisateur lance la commande de démarrage documentée
- **THEN** l'application répond sur `127.0.0.1` et refuse les connexions venant d'une autre adresse

#### Scenario: Documented warning
- **WHEN** l'utilisateur lit le README du tableau de bord
- **THEN** il y trouve l'interdiction d'exposer le port, en français

### Requirement: Shared database
L'application SHALL lire et écrire le fichier SQLite du Dénicheur, dont le chemin vient de la variable `DB_PATH` (par défaut `../denicheur.db`), sans créer ni migrer de tables. Un fichier absent ou sans le schéma attendu SHALL produire un message d'erreur en français et SHALL laisser le fichier intact.

#### Scenario: Custom path
- **WHEN** `DB_PATH` désigne une base valide
- **THEN** les pages affichent les données de cette base

#### Scenario: Missing database
- **WHEN** `DB_PATH` désigne un fichier inexistant
- **THEN** la page affiche « Base introuvable » avec le chemin demandé et aucun fichier n'est créé

### Requirement: Concurrent writers
Le tableau de bord SHALL pouvoir écrire pendant que le bot ou le run utilisent la base : une écriture bloquée par un autre processus SHALL attendre quelques secondes puis, en cas d'échec, afficher un message d'erreur en français sans perdre la saisie.

#### Scenario: Busy database
- **WHEN** la base est verrouillée plus longtemps que le délai d'attente pendant un changement de statut
- **THEN** l'utilisateur voit « Base occupée, réessaie » et le statut reste inchangé

### Requirement: Changes only through forms
Toute modification de la base SHALL passer par un formulaire envoyé par l'utilisateur. Les pages en lecture seule SHALL ne rien écrire, et l'application SHALL ne jamais envoyer de candidature, de message ni d'e-mail.

#### Scenario: Page view
- **WHEN** l'utilisateur ouvre une page
- **THEN** aucune ligne de la base n'est créée ni modifiée

### Requirement: French interface
Tout texte visible de l'application SHALL être en français ; la page SHALL être utilisable au clavier, avec des libellés associés aux champs et un contraste suffisant.

#### Scenario: Keyboard use
- **WHEN** l'utilisateur change un statut sans souris
- **THEN** les contrôles sont atteignables au clavier, nommés, et la validation soumet le formulaire
