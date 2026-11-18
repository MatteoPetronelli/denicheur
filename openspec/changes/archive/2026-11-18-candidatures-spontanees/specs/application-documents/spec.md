# Spec Delta

## ADDED Requirements

### Requirement: Spontaneous letter files
Pour une candidature spontanée, le service SHALL écrire les mêmes PDF et DOCX, nommés « Lettre de motivation <entreprise> » avec les mêmes règles d'assainissement et de non-écrasement, avec l'objet « Candidature spontanée » au lieu d'un poste. Le message d'accompagnement SHALL être un gabarit fixe, sans appel au modèle, qui parle d'une candidature spontanée et ne cite aucun poste.

#### Scenario: Files for a company
- **WHEN** une lettre est générée pour une entreprise
- **THEN** un PDF et un DOCX « Lettre de motivation <entreprise> » existent et leur objet est « Candidature spontanée »

#### Scenario: Fixed cover message
- **WHEN** le message d'accompagnement d'une entreprise est produit
- **THEN** il mentionne une candidature spontanée, la signature du candidat et aucun poste, et le modèle n'est pas appelé
