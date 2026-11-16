# Spec Delta

## Purpose

Réduire les offres collectées à celles qui méritent d'être notées : dédoublonnage, distance au centre, signalement des lieux douteux et rejet motivé par des règles déterministes.

## ADDED Requirements

### Requirement: Text normalization and dedupe key
Les comparaisons de texte SHALL ignorer casse, accents, mention « h/f » et espaces multiples ; la clé de dédoublonnage SHALL être un hachage stable de entreprise, titre et commune normalisés.

#### Scenario: Equivalent titles
- **WHEN** deux offres ne diffèrent que par accents, casse ou « H/F »
- **THEN** leurs clés de dédoublonnage sont identiques

### Requirement: Deduplication
Le dédoublonnage SHALL écarter les offres dont l'URL ou la clé est déjà connue, ou répétée dans le lot.

#### Scenario: Fixture
- **WHEN** les 16 offres de la fixture sont dédoublonnées sur une base vide
- **THEN** il en reste 10 et les paires Wavestone partagent la même clé

### Requirement: Distance filter
Le filtre géographique SHALL calculer la distance au centre ; au-delà du rayon l'offre reçoit le motif `hors_zone`.

#### Scenario: Known distance
- **WHEN** la distance Mareil-Marly → Paris 20e est calculée
- **THEN** elle vaut 23,2 km à ±0,3 km

#### Scenario: Outside radius
- **WHEN** une offre est à 30 km avec un rayon de 25 km
- **THEN** son motif de rejet est `hors_zone`

### Requirement: Unknown or doubtful location
Une offre sans coordonnées, ou dont la description cite en mot entier une ville de `config/villes_hors_zone.txt` différente de sa commune, SHALL être gardée avec `lieu_a_verifier` vrai.

#### Scenario: Missing coordinates
- **WHEN** une offre n'a ni latitude ni longitude
- **THEN** elle n'est pas rejetée et `lieu_a_verifier` est vrai

#### Scenario: Description names another city
- **WHEN** la description de l'offre Woodoo cite Troyes alors que la commune est autre
- **THEN** `lieu_a_verifier` est vrai, alors qu'il est faux pour ITIC

### Requirement: Prefilter rules
Le préfiltre SHALL appliquer dans l'ordre `piste_autre`, `expiree`, `trop_ancienne`, `mot_exclu:<mot>`, `mots_cles_absents`, `teletravail_complet` ; la première règle déclenchée donne le motif. Les offres rejetées restent dans le résultat avec leur motif.

#### Scenario: Retained offers on fixture
- **WHEN** la fixture est filtrée avec `now = 2026-11-16T09:00+01:00`
- **THEN** exactement ITIC et Woodoo n'ont pas de motif de rejet

#### Scenario: Excluded word
- **WHEN** le titre contient « Confirmé » (Capgemini)
- **THEN** le motif est `mot_exclu:confirme`

#### Scenario: Missing keywords
- **WHEN** le titre ne contient aucun mot-clé (MGEN, Wavestone récent)
- **THEN** le motif est `mots_cles_absents`

#### Scenario: Too old
- **WHEN** une offre est publiée il y a plus de 30 jours
- **THEN** le motif est `trop_ancienne`
