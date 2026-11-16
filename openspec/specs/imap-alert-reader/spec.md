# imap-alert-reader Specification

## Purpose
Lire les e-mails d'alerte d'offres reçus dans le libellé Gmail `Denicheur` sans jamais modifier la boîte aux lettres de l'utilisateur.

## Requirements

### Requirement: Read-only alert fetch
`lire_alertes(user, password, since, imap_factory)` SHALL ouvrir le libellé `Denicheur` en lecture seule, rechercher les messages depuis `since`, les récupérer avec `BODY.PEEK` et retourner les messages `email.message.Message` analysés. Elle SHALL NOT émettre de commande qui change des drapeaux, déplace ou supprime un message.

#### Scenario: Messages returned
- **WHEN** le faux serveur IMAP contient deux messages depuis `since`
- **THEN** la fonction retourne deux `Message` analysés

#### Scenario: Mailbox untouched
- **WHEN** la fonction s'exécute
- **THEN** le libellé est sélectionné en lecture seule, la récupération utilise `BODY.PEEK` et aucune commande `STORE`, `COPY`, `MOVE` ou `EXPUNGE` n'est émise

### Requirement: Session cleanup
La fonction SHALL fermer la session IMAP (`close` puis `logout`) y compris quand la recherche ou la récupération échoue.

#### Scenario: Fetch fails
- **WHEN** la récupération lève une exception
- **THEN** `logout` est tout de même appelé et l'exception remonte

### Requirement: Credentials stay out of logs
Le mot de passe d'application SHALL NOT apparaître dans un message d'erreur, une trace consignée ou la table `executions`.

#### Scenario: Authentication failure
- **WHEN** la connexion est refusée
- **THEN** l'erreur levée ne contient pas le mot de passe
