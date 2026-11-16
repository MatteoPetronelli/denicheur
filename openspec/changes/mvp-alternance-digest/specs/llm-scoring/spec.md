# Spec Delta

## Purpose

Noter chaque offre retenue de 0 à 100 avec un LLM local Ollama à sortie structurée, de façon reproductible, plafonnée en appels et en durée, sans jamais envoyer de données personnelles au modèle.

## ADDED Requirements

### Requirement: Structured score
Le scoring SHALL demander à Ollama une sortie JSON contrainte par le schéma `ScoreLLM` et SHALL stocker le score avec le modèle, les tokens et la durée.

#### Scenario: Valid response
- **WHEN** Ollama renvoie un JSON valide pour une offre
- **THEN** une ligne de score est stockée avec `modele`, `prompt_tokens`, `output_tokens` et `duree_s`

#### Scenario: Score out of range
- **WHEN** la réponse contient `score: 120`
- **THEN** la validation échoue et aucune ligne de score n'est créée

#### Scenario: Invalid JSON
- **WHEN** le contenu n'est pas un JSON valide
- **THEN** aucune ligne n'est créée, l'erreur est journalisée et l'offre est retentée au run suivant

### Requirement: Score cache
Une offre déjà notée SHALL NOT être renotée.

#### Scenario: Second run
- **WHEN** le scoring s'exécute deux fois sur les mêmes offres
- **THEN** le second passage ne fait aucun appel LLM

### Requirement: Call and duration caps
Le scoring SHALL s'arrêter quand `llm_max_appels_jour` appels ont été faits aujourd'hui ou quand `llm_max_duree_run_s` est dépassé ; les offres restantes attendent le run suivant. Une tentative invalide compte dans le plafond.

#### Scenario: Daily cap
- **WHEN** le plafond est 1 et deux offres attendent
- **THEN** un seul appel est fait

#### Scenario: Run duration limit
- **WHEN** la durée cumulée du run atteint la limite
- **THEN** les offres restantes ne sont pas notées

### Requirement: Ollama unavailable
Si Ollama refuse la connexion, le scoring SHALL être sauté pour le run, l'erreur enregistrée, sans lever d'exception.

#### Scenario: Connection refused
- **WHEN** l'appel échoue par connexion refusée
- **THEN** le run continue et l'erreur figure dans les erreurs de l'exécution

### Requirement: Config-driven model options
Le modèle et les options (température, `num_ctx`, timeout) SHALL venir de la config selon le type de requête, jamais surchargés dans le code.

#### Scenario: Request payload
- **WHEN** une requête de scoring est émise
- **THEN** son modèle et ses options sont ceux de `llm.scoring`

### Requirement: No PII in prompts
Les prompts SHALL être construits uniquement à partir de `profile/profil.md` et de l'offre ; le prompt système SHALL être identique d'un appel à l'autre (sans date ni identifiant), la date du jour figurant dans le message utilisateur.

#### Scenario: PII scan
- **WHEN** le prompt complet est construit pour une offre de la fixture
- **THEN** il ne contient ni motif de téléphone, ni `@`, ni « né le »

#### Scenario: Stable prefix
- **WHEN** deux prompts sont construits à des dates différentes
- **THEN** leurs messages système sont identiques

### Requirement: Model comparison
Un script SHALL comparer plusieurs modèles sur des offres étiquetées et afficher l'écart moyen absolu, le nombre d'offres franchissant le seuil de 65 et la durée totale.

#### Scenario: Dry run
- **WHEN** le script s'exécute avec `--dry-run`
- **THEN** il utilise le scoreur factice et affiche les trois métriques sans appeler Ollama
