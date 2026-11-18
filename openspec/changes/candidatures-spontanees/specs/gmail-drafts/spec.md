# Spec Delta

## ADDED Requirements

### Requirement: Spontaneous draft subject
Le sujet du brouillon Gmail d'une candidature spontanée SHALL être « Candidature spontanée : <entreprise> », nettoyé de tout saut de ligne. Le destinataire SHALL rester vide quand aucune adresse n'est connue.

#### Scenario: Subject with a hostile name
- **WHEN** le nom de l'entreprise contient un saut de ligne et un faux en-tête
- **THEN** le sujet tient sur une seule ligne et aucun en-tête n'est injecté

#### Scenario: No recipient
- **WHEN** un brouillon d'entreprise est déposé
- **THEN** l'en-tête `To` est absent ou vide
