# Spec Delta

## ADDED Requirements

### Requirement: Company import command
La sous-commande `import-entreprises <fichier>` SHALL importer le CSV indiqué dans la base et afficher en français le nombre d'entreprises créées, mises à jour et ignorées. Un fichier absent ou illisible SHALL donner un message en français sans trace d'erreur et le code 1.

#### Scenario: Import
- **WHEN** l'utilisateur lance `py -m denicheur import-entreprises entreprises_spontanees_mareil-marly.csv`
- **THEN** la sortie indique les nombres créées, mises à jour et ignorées, et le code de sortie est 0

#### Scenario: Missing file
- **WHEN** le fichier n'existe pas
- **THEN** un message en français s'affiche, sans trace d'erreur, et le code de sortie est 1
