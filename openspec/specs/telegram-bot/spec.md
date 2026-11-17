# telegram-bot Specification

## Purpose
Permettre d'agir sur les offres depuis Telegram (boutons et commandes) en ne servant que le chat autorisé et en ne traitant chaque mise à jour qu'une fois.

## Requirements

### Requirement: Authorized chat only
Le bot SHALL ignorer sans aucune réponse ni appel à l'API Telegram toute mise à jour (message ou appui sur bouton) dont le chat n'est pas `TELEGRAM_CHAT_ID`, et SHALL ne jamais écrire dans un autre chat.

#### Scenario: Foreign message
- **WHEN** un message arrive d'un chat différent du chat autorisé
- **THEN** aucune réponse n'est envoyée, aucune commande n'est exécutée et la base n'est pas modifiée

#### Scenario: Foreign button
- **WHEN** un appui sur bouton arrive d'un chat étranger
- **THEN** la base n'est pas modifiée

### Requirement: Each update handled once
Chaque `update_id` SHALL être traité une seule fois : le bot SHALL mémoriser le dernier traité (`dernier_update_id`), ignorer tout `update_id` inférieur ou égal et reprendre au suivant après un redémarrage.

#### Scenario: Duplicate update
- **WHEN** le même `update_id` est reçu deux fois
- **THEN** l'action n'est exécutée qu'une fois

#### Scenario: Restart
- **WHEN** le bot redémarre après avoir traité l'update 41
- **THEN** il demande les mises à jour à partir de 42

### Requirement: Resilient polling loop
La boucle SHALL supprimer le webhook une fois au démarrage, interroger Telegram en long polling, et SHALL continuer après une erreur réseau ou Telegram en attendant brièvement ; une erreur sur une mise à jour SHALL NOT empêcher de traiter les suivantes.

#### Scenario: Network error
- **WHEN** l'appel de récupération des mises à jour échoue
- **THEN** la boucle attend puis réessaie sans s'arrêter

#### Scenario: Failing update
- **WHEN** le traitement d'une mise à jour lève une erreur
- **THEN** la suivante est tout de même traitée et l'erreur est journalisée sans jeton

### Requirement: Offer buttons
Les boutons d'une offre SHALL agir ainsi : « Je postule » marque la candidature envoyée à la date du jour et remplace le clavier par « ✅ Envoyée » ; « Rappel » marque l'offre `interessante` ; « Ignorer » la marque `ignoree` ; « Brouillon » répond « ⏳ Rédaction… », génère un brouillon d'e-mail, l'enregistre et l'envoie dans Telegram avec un bouton « 📥 Créer le brouillon Gmail ». Chaque appui SHALL recevoir une réponse de prise en compte, y compris refusé ou répété.

#### Scenario: I apply
- **WHEN** l'utilisateur appuie sur « Je postule » d'une offre sans suivi
- **THEN** la candidature est `candidature_envoyee` avec `envoyee_le` du jour, le clavier affiche « ✅ Envoyée » et l'appui reçoit une réponse

#### Scenario: Pressed twice
- **WHEN** « Je postule » est pressé une seconde fois
- **THEN** la base ne change pas et l'appui reçoit une réponse indiquant que c'est déjà fait

#### Scenario: Refused transition
- **WHEN** « Je postule » est pressé sur une offre `ignoree`
- **THEN** la base ne change pas et l'appui reçoit une réponse expliquant le refus

#### Scenario: Unknown offer in button
- **WHEN** l'identifiant d'offre du bouton n'existe pas
- **THEN** l'appui reçoit une réponse d'erreur et la base ne change pas

#### Scenario: Draft requested
- **WHEN** l'utilisateur appuie sur « Brouillon » d'une offre
- **THEN** l'appui reçoit « ⏳ Rédaction… », un brouillon est enregistré, et un message contient le texte avec le bouton « 📥 Créer le brouillon Gmail »

#### Scenario: Draft on an ignored offer
- **WHEN** « Brouillon » est pressé sur une offre `ignoree`
- **THEN** aucun brouillon n'est généré et l'appui reçoit une réponse expliquant le refus

### Requirement: Malformed callback data
Une donnée de bouton inconnue ou mal formée SHALL recevoir une réponse neutre sans modifier la base ni lever d'erreur.

#### Scenario: Garbage callback
- **WHEN** la donnée du bouton vaut `zzz`
- **THEN** l'appui reçoit une réponse et la base ne change pas

### Requirement: Commands
Le bot SHALL répondre en français à `/aujourdhui` (offres notifiées du jour sans suivi), `/stage` et `/alternance` (meilleures offres notées non écartées de la piste), `/candidatures` (suivi en cours), `/relances` (candidatures à relancer), `/stats`, `/config` (paramètres non secrets) ; `/pause` et `/reprendre` SHALL fixer le paramètre `pause` à `1` ou `0`. Une commande inconnue SHALL recevoir la liste des commandes.

#### Scenario: Pause and resume
- **WHEN** l'utilisateur envoie `/pause` puis `/reprendre`
- **THEN** `pause` vaut `1` puis `0`, avec une confirmation à chaque fois

#### Scenario: Config hides secrets
- **WHEN** l'utilisateur envoie `/config`
- **THEN** la réponse ne contient ni jeton, ni clé, ni mot de passe, ni identifiant de chat

#### Scenario: Unknown command
- **WHEN** l'utilisateur envoie `/bidule`
- **THEN** la réponse liste les commandes disponibles

### Requirement: Safe message text
Tout texte issu d'une offre inséré dans une réponse SHALL être échappé pour le mode HTML de Telegram, et toute réponse SHALL tenir dans 4096 caractères.

#### Scenario: Hostile title
- **WHEN** un titre d'offre contient `<b>` et qu'il apparaît dans `/candidatures`
- **THEN** la réponse contient `&lt;b&gt;`

### Requirement: Gmail draft button
« 📥 Créer le brouillon Gmail » SHALL déposer le texte du brouillon dans les brouillons Gmail sans la ligne « Éléments du profil utilisés » ni les notes de contrôle, marquer le brouillon comme déposé, et répondre en français. Un brouillon déjà déposé SHALL ne l'être qu'une fois ; une défaillance IMAP SHALL produire un message sans secret et laisser le brouillon non déposé.

#### Scenario: Draft created
- **WHEN** l'utilisateur appuie sur « 📥 Créer le brouillon Gmail » d'un brouillon non déposé
- **THEN** un seul brouillon est ajouté dans Gmail, le brouillon est marqué déposé et l'appui reçoit une réponse de confirmation

#### Scenario: Pressed twice
- **WHEN** le même bouton est pressé une seconde fois
- **THEN** aucun second brouillon n'est ajouté et l'appui indique que c'est déjà fait

#### Scenario: Gmail unavailable
- **WHEN** l'ajout IMAP échoue
- **THEN** la réponse est un message d'échec sans identifiant ni mot de passe et le brouillon reste non déposé

#### Scenario: Unknown draft
- **WHEN** l'identifiant du brouillon n'existe pas
- **THEN** l'appui reçoit une réponse d'erreur et rien n'est ajouté dans Gmail

### Requirement: Follow-up button
« ✉️ Relance » SHALL générer un brouillon de relance pour la candidature, l'enregistrer et l'envoyer avec le bouton « 📥 Créer le brouillon Gmail ». Une seule relance SHALL être possible par candidature : une seconde demande reçoit un refus en français sans nouvel appel au modèle.

#### Scenario: First follow-up
- **WHEN** l'utilisateur appuie sur « ✉️ Relance » d'une candidature envoyée
- **THEN** un brouillon de relance est enregistré et envoyé avec le bouton Gmail

#### Scenario: Second follow-up refused
- **WHEN** « ✉️ Relance » est pressé de nouveau pour la même candidature
- **THEN** l'appui reçoit un refus, aucun appel au modèle n'a lieu et aucun brouillon n'est ajouté

### Requirement: Letter button
« 📄 Lettre PDF » SHALL générer une lettre de 250 à 300 mots, l'enregistrer comme brouillon `lettre` et écrire un PDF et un DOCX dans le dossier des lettres, puis envoyer le texte relu, les deux fichiers et le message d'accompagnement avec le bouton Gmail. Le dépôt Gmail d'une lettre SHALL joindre le PDF.

#### Scenario: Letter generated
- **WHEN** l'utilisateur appuie sur « 📄 Lettre PDF » d'une offre
- **THEN** l'appui reçoit « ⏳ Rédaction… », un brouillon `lettre` est enregistré et le PDF et le DOCX sont écrits
- **AND** le chat reçoit d'abord le texte relu avec sa ligne « Éléments du profil utilisés » (absente des fichiers), puis les deux fichiers, puis le message d'accompagnement avec le bouton Gmail

#### Scenario: Gmail draft with attachment
- **WHEN** l'utilisateur appuie sur « 📥 Créer le brouillon Gmail » d'un brouillon de lettre
- **THEN** un seul brouillon Gmail est créé, avec le PDF en pièce jointe et le message d'accompagnement en corps

#### Scenario: Ignored offer
- **WHEN** « 📄 Lettre PDF » est pressé sur une offre `ignoree`
- **THEN** aucun appel au modèle n'a lieu et aucun fichier n'est écrit

#### Scenario: Files cannot be written
- **WHEN** l'écriture des fichiers échoue
- **THEN** l'utilisateur reçoit un message d'échec sans chemin ni donnée personnelle, aucun brouillon n'est enregistré et le bot continue de répondre

### Requirement: Writing failures stay contained
Une défaillance de la rédaction (Ollama arrêté, délai dépassé, fichier de profil absent) SHALL produire un message en français sans détail interne, ne SHALL enregistrer aucun brouillon et ne SHALL pas interrompre la boucle de polling.

#### Scenario: Ollama stopped
- **WHEN** « Brouillon » est pressé alors qu'Ollama est arrêté
- **THEN** l'utilisateur reçoit un message d'échec et le bot continue de répondre aux appuis suivants
