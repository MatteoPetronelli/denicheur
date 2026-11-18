# Spec Delta

## ADDED Requirements

### Requirement: Company message and buttons
Le message d'une entreprise SHALL afficher en français son nom, son activité, sa commune, sa distance et son lien de candidature spontanée s'il existe, avec quatre boutons : « ✉️ Brouillon spontané » (`s:<id>`), « 📄 Lettre PDF » (`t:<id>`), « ✅ Envoyée » (`e:<id>`) et « ❌ Ignorer » (`i:<id>`). Chaque appui SHALL recevoir une réponse de prise en compte, y compris refusé ou répété, et l'identifiant ne SHALL accepter que des chiffres.

#### Scenario: Company message
- **WHEN** une entreprise est envoyée
- **THEN** le message contient son nom, son activité et sa commune, avec les quatre boutons

#### Scenario: Open offer at the same company
- **WHEN** une offre non rejetée porte le SIRET de l'entreprise
- **THEN** le message ajoute « 📌 Offre ouverte aussi : » suivi du titre de l'offre, échappé pour HTML

#### Scenario: Sent
- **WHEN** l'utilisateur appuie sur « ✅ Envoyée »
- **THEN** l'entreprise est contactée, le clavier devient « ✅ Envoyée » inerte et l'appui reçoit une réponse

#### Scenario: Pressed twice
- **WHEN** « ✅ Envoyée » ou « ❌ Ignorer » est pressé une seconde fois
- **THEN** la base ne change pas et l'appui reçoit une réponse indiquant que c'est déjà fait

#### Scenario: Unknown company in button
- **WHEN** l'identifiant d'entreprise du bouton n'existe pas
- **THEN** l'appui reçoit une réponse d'erreur et la base ne change pas

### Requirement: Company draft buttons
« ✉️ Brouillon spontané » SHALL répondre « ⏳ Rédaction… », générer un message `spontanee`, l'enregistrer et l'envoyer avec le bouton « 📥 Créer le brouillon Gmail ». « 📄 Lettre PDF » SHALL générer une lettre `lettre`, écrire le PDF et le DOCX dans le dossier des lettres, puis envoyer le texte relu, les deux fichiers et le message d'accompagnement avec le même bouton Gmail.

#### Scenario: Message draft
- **WHEN** l'utilisateur appuie sur « ✉️ Brouillon spontané » d'une entreprise
- **THEN** un brouillon `spontanee` est enregistré et envoyé avec le bouton « 📥 Créer le brouillon Gmail »

#### Scenario: Letter draft
- **WHEN** l'utilisateur appuie sur « 📄 Lettre PDF » d'une entreprise
- **THEN** un brouillon `lettre` est enregistré, un PDF et un DOCX existent dans le dossier des lettres et sont envoyés dans Telegram, avec le message d'accompagnement

### Requirement: Company draft refusals and Gmail deposit
Une entreprise écartée, contactée ou au plafond du jour SHALL recevoir une réponse expliquant le refus, sans appel au modèle. Le dépôt Gmail d'un brouillon d'entreprise SHALL créer un brouillon sans destinataire, avec le PDF joint pour une lettre.

#### Scenario: Daily cap reached
- **WHEN** le seizième brouillon d'entreprise du jour est demandé
- **THEN** l'appui reçoit une réponse expliquant que le plafond du jour est atteint et le modèle n'est pas appelé

#### Scenario: Ignored company
- **WHEN** « ✉️ Brouillon spontané » est pressé sur une entreprise écartée
- **THEN** aucun brouillon n'est généré et l'appui reçoit une réponse expliquant le refus

#### Scenario: Gmail deposit of a company draft
- **WHEN** l'utilisateur appuie sur « 📥 Créer le brouillon Gmail » d'un brouillon d'entreprise
- **THEN** un brouillon « Candidature spontanée : <entreprise> » sans destinataire est déposé, avec le PDF joint pour une lettre
