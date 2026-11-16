## ADDED Requirements

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
Les boutons d'une offre SHALL agir ainsi : « Je postule » marque la candidature envoyée à la date du jour et remplace le clavier par « ✅ Envoyée » ; « Rappel » marque l'offre `interessante` ; « Ignorer » la marque `ignoree` ; « Brouillon » répond « Brouillon disponible à l'étape C5 ». Chaque appui SHALL recevoir une réponse de prise en compte, y compris refusé ou répété.

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
