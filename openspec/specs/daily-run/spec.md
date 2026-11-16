# daily-run Specification

## Purpose
Exécuter automatiquement et de façon idempotente le cycle collecte, filtrage, scoring, notification, le consigner en base et le planifier via le Planificateur de tâches Windows.

## Requirements

### Requirement: Execution record
Chaque exécution SHALL créer une ligne `executions` avec le mode, les compteurs (collectées, retenues, scorées, notifiées), les erreurs et la durée LLM.

#### Scenario: Normal run
- **WHEN** `executer` tourne sur la fixture avec des fakes
- **THEN** une ligne `executions` existe avec les compteurs attendus

### Requirement: Due sources
Les sources d'offres d'alternance SHALL être collectées si la dernière collecte date d'au moins 3 h et qu'il est entre 08:00 et 20:00 Paris ; un run tardif rattrape un run manqué. `--mode alternance` SHALL forcer cette seule collecte.

#### Scenario: Recent collection
- **WHEN** une collecte d'alternance a eu lieu il y a moins de 3 h
- **THEN** aucune nouvelle collecte d'alternance n'est faite

### Requirement: Stage sources due once a day
Les sources de stage SHALL être collectées une seule fois par jour Paris, entre 08:00 et 20:00, tant que la date de la dernière collecte de stage n'est pas celle du jour ; `--mode stage` SHALL forcer cette collecte sans collecter l'alternance.

#### Scenario: Stage collected once a day
- **WHEN** `run --mode auto` tourne à 09:00 Paris et que la dernière collecte de stage date de la veille
- **THEN** les sources de stage sont collectées et la date du jour est enregistrée

#### Scenario: Stage already collected today
- **WHEN** la dernière collecte de stage porte la date du jour Paris
- **THEN** aucune source de stage n'est collectée

#### Scenario: Forced stage mode
- **WHEN** `run --mode stage` tourne hors plage horaire, même si la collecte du jour est faite
- **THEN** les sources de stage sont collectées et celles d'alternance ne le sont pas

#### Scenario: Stage error isolated
- **WHEN** la source Adzuna lève une erreur
- **THEN** l'erreur est consignée sans la clé et la collecte d'alternance de ce run n'est pas affectée

### Requirement: Optional sources need credentials
La source e-mail SHALL faire partie des sources collectées lorsque `GMAIL_USER` et `GMAIL_APP_PASSWORD` sont présents, et la source Adzuna lorsque `ADZUNA_APP_ID` et `ADZUNA_APP_KEY` sont présents ; elles SHALL être absentes sinon, sans erreur.

#### Scenario: Email source enabled
- **WHEN** les identifiants Gmail sont présents
- **THEN** la source `email` figure parmi les sources collectées par `run`

#### Scenario: Email source disabled
- **WHEN** `GMAIL_APP_PASSWORD` est absent
- **THEN** `run` ne contient pas la source `email` et ne signale aucune erreur

#### Scenario: Adzuna source disabled
- **WHEN** `ADZUNA_APP_KEY` est absent
- **THEN** `run` ne contient pas de source de stage et ne signale aucune erreur

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
