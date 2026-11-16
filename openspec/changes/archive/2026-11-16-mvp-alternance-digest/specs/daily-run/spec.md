# Spec Delta

## Purpose

Exécuter automatiquement et de façon idempotente le cycle collecte, filtrage, scoring, notification, le consigner en base et le planifier via le Planificateur de tâches Windows.

## ADDED Requirements

### Requirement: Execution record
Chaque exécution SHALL créer une ligne `executions` avec le mode, les compteurs (collectées, retenues, scorées, notifiées), les erreurs et la durée LLM.

#### Scenario: Normal run
- **WHEN** `executer` tourne sur la fixture avec des fakes
- **THEN** une ligne `executions` existe avec les compteurs attendus

### Requirement: Due sources
Les sources alternance SHALL être collectées si la dernière collecte date d'au moins 3 h et qu'il est entre 08:00 et 20:00 Paris ; un run tardif rattrape un run manqué.

#### Scenario: Recent collection
- **WHEN** une collecte alternance a eu lieu il y a moins de 3 h
- **THEN** aucune nouvelle collecte n'est faite

### Requirement: Source isolation
Une source en erreur SHALL être consignée dans `executions.erreurs` sans interrompre le run.

#### Scenario: Source raises
- **WHEN** une source lève une exception
- **THEN** l'erreur est enregistrée et les autres étapes s'exécutent

### Requirement: Instant alerts
Une offre alternance de score ≥ `alerte_immediate_alternance_min`, non notifiée, entre 08:00 et 20:00 Paris SHALL déclencher un message « 🚨 Alternance » et ne SHALL pas être répétée dans le digest.

#### Scenario: Woodoo alert
- **WHEN** Woodoo a un score de 85 à 10:00 Paris
- **THEN** une alerte est envoyée, puis elle est absente du digest

### Requirement: Digest timing and idempotence
Le digest SHALL être envoyé une seule fois par jour, à partir de `heure_digest` Paris ; chaque offre SHALL être envoyée au plus une fois et notée une seule fois.

#### Scenario: Before digest hour
- **WHEN** le run a lieu à 07:00 Paris
- **THEN** aucun digest n'est envoyé

#### Scenario: Twice the same day
- **WHEN** `executer` tourne à 08:31 puis de nouveau le même jour
- **THEN** le digest est envoyé une fois seulement

### Requirement: Pause switch
Si le paramètre `pause` vaut `1`, le run SHALL collecter et noter mais ne rien envoyer.

#### Scenario: Paused
- **WHEN** `pause == "1"`
- **THEN** aucun message n'est envoyé

### Requirement: Degraded scoring
Si Ollama est injoignable, les offres déjà notées SHALL tout de même être notifiées.

#### Scenario: Ollama down
- **WHEN** le scoring échoue par connexion refusée
- **THEN** les offres déjà notées sont envoyées

### Requirement: Failure notice
Une exception non gérée SHALL clore l'exécution en erreur, envoyer « ⚠️ La collecte du jour a échoué : <type d'erreur> » sans trace ni secret, et rendre le code de sortie 1.

#### Scenario: Uncaught error
- **WHEN** une étape lève une exception inattendue
- **THEN** le message d'échec est envoyé et le code de sortie vaut 1

### Requirement: Scheduled task installer
`scripts/installer_taches.ps1` SHALL enregistrer, sans droits administrateur, une tâche Windows lançant `run --mode auto` dans le dépôt toutes les heures de 08:30 sur 12 h, avec rattrapage, une seule instance et sortie ajoutée à `logs/run.log` ; le relancer SHALL remplacer la tâche.

#### Scenario: Reinstall
- **WHEN** le script est exécuté deux fois
- **THEN** une seule tâche `Denicheur` existe
