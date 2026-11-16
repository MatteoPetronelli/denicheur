# Spec Delta

## Purpose

Transformer les e-mails d'alerte d'offres en offres normalisées du pipeline, sans visiter les pages des sites et sans conserver de donnée personnelle.

## ADDED Requirements

### Requirement: Per-sender parsing
Chaque expéditeur reconnu (Indeed et Jobtome ; Welcome to the Jungle, LinkedIn et JobTeaser dès qu'un e-mail réel existe), identifié par le domaine de l'en-tête `From`, SHALL avoir un analyseur qui extrait pour chaque offre le titre, l'entreprise, la ville et le lien. Un expéditeur inconnu SHALL produire zéro offre et une ligne de journal, sans exception.

#### Scenario: Known sender
- **WHEN** un e-mail de la fixture de chaque expéditeur est analysé
- **THEN** le nombre d'offres extraites égale le nombre attendu pour cet e-mail

#### Scenario: Unknown sender
- **WHEN** l'e-mail vient d'un domaine non géré
- **THEN** zéro offre est retournée et le domaine est consigné

### Requirement: Clean links and stable identity
Le lien d'une offre SHALL être débarrassé des paramètres de suivi et du fragment ; `source` SHALL valoir `email:<site>` et `source_id` le SHA-1 du lien propre, ou de son chemin seul quand la requête du lien porte un jeton propre au destinataire (Jobtome).

#### Scenario: Same offer in two e-mails
- **WHEN** la même offre apparaît dans deux e-mails avec des paramètres de suivi différents
- **THEN** elles ont le même lien propre et une seule subsiste après dédoublonnage

### Requirement: Piste from title
La piste SHALL être `alternance` si le titre contient « alternance », « alternant », « apprentissage » ou « apprenti », `stage` s'il contient « stage » ou « stagiaire », sinon `autre`.

#### Scenario: Alternance title
- **WHEN** le titre est « Alternance développeur web »
- **THEN** la piste vaut `alternance`

#### Scenario: Other title
- **WHEN** le titre ne contient aucun de ces mots
- **THEN** la piste vaut `autre`

### Requirement: Location geocoding
La commune SHALL être géocodée via `api-adresse.data.gouv.fr` avec un cache en mémoire par commune ; sans coordonnées obtenues, l'offre SHALL avoir `lat` et `lon` à `None` afin que le pipeline la marque « lieu à vérifier ».

#### Scenario: Geocoding succeeds
- **WHEN** l'API renvoie des coordonnées pour « Versailles »
- **THEN** l'offre porte ces coordonnées et un seul appel est fait pour deux offres de la même commune

#### Scenario: Geocoding fails
- **WHEN** l'API est indisponible
- **THEN** l'offre est conservée avec coordonnées vides, sans exception

### Requirement: No personal data kept
La description d'une offre SHALL contenir uniquement le texte du bloc de l'offre ; salutations, adresse du destinataire et liens de désabonnement SHALL être exclus.

#### Scenario: Recipient data excluded
- **WHEN** une offre est extraite d'un e-mail adressé à l'utilisateur
- **THEN** ni l'adresse e-mail du destinataire ni son nom n'apparaissent dans la description

### Requirement: Source skipped without credentials
Si `GMAIL_USER` ou `GMAIL_APP_PASSWORD` est absent ou vide, la source SHALL être ignorée, avec une ligne de journal et sans connexion réseau.

#### Scenario: Missing app password
- **WHEN** `GMAIL_APP_PASSWORD` est vide
- **THEN** la collecte retourne zéro offre sans ouvrir de connexion IMAP
