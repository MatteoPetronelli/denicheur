# Spec Delta

## ADDED Requirements

### Requirement: Company drafts
Le service SHALL produire pour une entreprise, sans offre ni score, un brouillon `spontanee` (120 à 180 mots) ou `lettre` (250 à 300 mots) en français et au vouvoiement. Le type `relance` ou inconnu SHALL être refusé avant tout appel au modèle. Les textes SHALL annoncer l'alternance (1 semaine d'école pour 2 semaines en entreprise, dès que possible) et citer un projet du profil.

#### Scenario: Spontaneous message
- **WHEN** un brouillon `spontanee` est demandé pour une entreprise
- **THEN** le texte est en français, cite le nom de l'entreprise, un projet du profil et la disponibilité en alternance

#### Scenario: Follow-up refused
- **WHEN** une relance est demandée pour une entreprise
- **THEN** le service lève une erreur et le modèle n'est pas appelé

### Requirement: Company prompt carries no invention
Le message utilisateur d'une entreprise SHALL contenir uniquement son nom, son activité, sa commune et la consigne de ne rien affirmer d'autre sur elle. Il ne SHALL contenir ni adresse e-mail, ni numéro de téléphone, ni donnée de dirigeant. Le texte livré SHALL être complet et prêt à envoyer, sans passage entre crochets.

#### Scenario: Prompt content
- **WHEN** le prompt d'une entreprise est construit
- **THEN** il contient son nom, son activité et sa commune, et aucune autre donnée de la base

#### Scenario: Placeholder removed
- **WHEN** le modèle renvoie un passage « [à compléter …] »
- **THEN** il est retiré du texte livré
