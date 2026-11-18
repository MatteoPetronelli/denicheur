# Spec Delta

## ADDED Requirements

### Requirement: Employer SIRET on offers
La source SHALL conserver sur chaque offre le SIRET de l'employeur quand l'API le fournit, et le laisser vide sinon. Un SIRET qui n'est pas composé de 14 chiffres SHALL être traité comme absent.

#### Scenario: SIRET present
- **WHEN** la source lit la fixture `lba_search.json`
- **THEN** les offres dont l'employeur a un SIRET le portent, et les autres ont un SIRET vide

#### Scenario: Malformed SIRET
- **WHEN** l'API renvoie un SIRET de 9 chiffres ou contenant des lettres
- **THEN** l'offre est conservée avec un SIRET vide
