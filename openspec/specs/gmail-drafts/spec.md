# gmail-drafts Specification

## Purpose
Déposer un texte relu dans les brouillons Gmail de l'utilisateur par IMAP pour qu'il l'envoie lui-même, sans jamais envoyer de message.

## Requirements

### Requirement: Draft stored in Gmail drafts
La création SHALL ajouter exactement un message au dossier des brouillons du compte, identifié par son attribut IMAP `\Drafts` (« [Gmail]/Brouillons » sur un compte en français, « [Gmail]/Drafts » en anglais), avec le drapeau `\Draft`, sujet et corps en UTF-8, destinataire vide ou fourni. Aucune lecture, aucun envoi et aucune modification d'un autre dossier ne SHALL avoir lieu.

#### Scenario: One draft appended
- **WHEN** un brouillon est créé avec un sujet et un corps accentués
- **THEN** l'IMAP factice reçoit exactement un `APPEND` dans le dossier portant l'attribut `\Drafts` (même s'il s'appelle « [Gmail]/Brouillons ») avec le drapeau `\Draft`, et le sujet et le corps sont lisibles intacts

#### Scenario: No recipient invented
- **WHEN** aucun destinataire n'est fourni
- **THEN** l'en-tête `To` est absent ou vide

#### Scenario: Drafts folder not found
- **WHEN** aucun dossier n'a l'attribut `\Drafts`
- **THEN** une erreur dédiée est levée sans secret et aucun `APPEND` n'a lieu

### Requirement: Never send
Le code SHALL n'utiliser aucun protocole d'envoi : le paquet de rédaction n'importe pas `smtplib` et aucune connexion SMTP n'est ouverte.

#### Scenario: No SMTP in the package
- **WHEN** les sources du paquet de rédaction sont analysées
- **THEN** aucune importation de `smtplib` n'y figure

### Requirement: Attachments
Le dépôt SHALL pouvoir joindre un ou plusieurs fichiers (type et nom conservés, contenu intact) au brouillon, dans le même et unique message : l'ajout reste exactement un `APPEND`.

#### Scenario: PDF attached
- **WHEN** un brouillon est créé avec un PDF en pièce jointe
- **THEN** l'IMAP factice reçoit un seul `APPEND` dont le message contient le corps et la pièce jointe, de type `application/pdf`, au nom et au contenu intacts

#### Scenario: Without attachment
- **WHEN** aucun fichier n'est fourni
- **THEN** le message ne contient aucune pièce jointe

### Requirement: Safe failures
Un échec de connexion, d'identification ou d'`APPEND` SHALL lever une erreur dédiée dont le message ne contient ni mot de passe ni adresse, et la connexion SHALL toujours être fermée.

#### Scenario: Login refused
- **WHEN** l'identification est refusée
- **THEN** l'erreur ne contient ni l'identifiant ni le mot de passe et la connexion est fermée

#### Scenario: Append refused
- **WHEN** le serveur répond autre chose que `OK` à l'`APPEND`
- **THEN** une erreur est levée et aucun brouillon n'est considéré comme créé

### Requirement: Spontaneous draft subject
Le sujet du brouillon Gmail d'une candidature spontanée SHALL être « Candidature spontanée : <entreprise> », nettoyé de tout saut de ligne. Le destinataire SHALL rester vide quand aucune adresse n'est connue.

#### Scenario: Subject with a hostile name
- **WHEN** le nom de l'entreprise contient un saut de ligne et un faux en-tête
- **THEN** le sujet tient sur une seule ligne et aucun en-tête n'est injecté

#### Scenario: No recipient
- **WHEN** un brouillon d'entreprise est déposé
- **THEN** l'en-tête `To` est absent ou vide
