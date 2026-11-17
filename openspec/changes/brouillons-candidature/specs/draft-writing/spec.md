## Purpose

Produire en local, avec le modèle d'écriture d'Ollama, un brouillon de candidature en français (e-mail, lettre, relance ou candidature spontanée) à partir du profil du candidat et d'une offre, sans rien inventer et sans exposer de donnée personnelle au modèle.

## ADDED Requirements

### Requirement: Draft types
Le service SHALL produire, pour une offre et son score, un brouillon d'un des types `email`, `lettre`, `relance` ou `spontanee`, en français et au vouvoiement. Un type inconnu SHALL être refusé avant tout appel au modèle.

#### Scenario: E-mail draft
- **WHEN** un brouillon `email` est demandé pour une offre
- **THEN** le texte est en français, cite un projet du profil adapté à l'offre et mentionne la disponibilité de la piste (stage : janvier ou février 2027, 5 à 6 mois ; alternance : 1 semaine d'école pour 2 semaines en entreprise)

#### Scenario: Unknown type
- **WHEN** un type hors de la liste est demandé
- **THEN** le service lève une erreur et le modèle n'est pas appelé

### Requirement: Stable system prompt without personal data
Le message système SHALL être composé uniquement de `profile/regles_ecriture.md`, `profile/lettre_modele.md` et `profile/profil.md`, identique d'une requête à l'autre du même type. Le prompt (système et utilisateur) SHALL ne jamais contenir le contenu de `profile/cv_*.md`, une adresse e-mail, un numéro de téléphone, un secret ni le contenu de `.env`.

#### Scenario: No personal data in the prompt
- **WHEN** un brouillon est demandé avec les fichiers de profil et un `.env` présents
- **THEN** le prompt envoyé au modèle ne contient ni le contenu des CV locaux, ni adresse e-mail, ni téléphone, ni secret

#### Scenario: Missing profile file
- **WHEN** `profile/regles_ecriture.md` ou `profile/lettre_modele.md` est absent
- **THEN** le service lève une erreur explicite en français et le modèle n'est pas appelé

### Requirement: Writing model from configuration
Le modèle et les options de rédaction SHALL venir de `llm.ecriture` dans la configuration, sans surcharge dans le code. Une erreur du modèle (Ollama arrêté, délai dépassé, réponse inutilisable) SHALL produire une erreur dédiée sans détail interne.

#### Scenario: Options come from the configuration
- **WHEN** un brouillon est demandé
- **THEN** la requête utilise le modèle, la température, le contexte et le délai de `llm.ecriture`

#### Scenario: Ollama stopped
- **WHEN** Ollama refuse la connexion
- **THEN** le service lève l'erreur d'indisponibilité et aucun brouillon n'est enregistré

### Requirement: Profile elements line
Tout brouillon SHALL se terminer par une ligne « Éléments du profil utilisés : … » listant ce qui a été utilisé, afin que l'utilisateur vérifie ce que le texte affirme. Un texte sans cette ligne SHALL être complété par une ligne indiquant que la vérification est impossible, sans masquer le brouillon.

#### Scenario: Line present
- **WHEN** le modèle répond avec la ligne finale
- **THEN** le brouillon la conserve en dernière ligne

#### Scenario: Line missing
- **WHEN** le modèle répond sans la ligne finale
- **THEN** le brouillon est livré avec une dernière ligne signalant l'absence de liste d'éléments

### Requirement: Length control
Un e-mail SHALL compter 120 à 180 mots et une lettre 250 à 300 mots, la ligne « Éléments du profil utilisés » exclue du décompte. Hors plage, le service SHALL refaire exactement un essai, puis livrer le meilleur des deux textes avec une note « ⚠️ longueur hors plage ». Les relances et candidatures spontanées SHALL suivre la plage de l'e-mail.

#### Scenario: In range
- **WHEN** le premier essai compte 150 mots pour un e-mail
- **THEN** un seul appel est fait et aucune note n'est ajoutée

#### Scenario: One retry
- **WHEN** le premier essai compte 90 mots pour un e-mail et le second 140
- **THEN** le texte du second essai est livré sans note

#### Scenario: Still out of range
- **WHEN** les deux essais sont hors plage
- **THEN** le texte le plus proche de la plage est livré avec la note « ⚠️ longueur hors plage » et il n'y a pas de troisième appel

### Requirement: No invented company detail
Quand rien dans l'offre n'établit un détail propre à l'entreprise, le brouillon SHALL contenir le marqueur littéral `[à compléter : détail sur l'entreprise]` à la place du détail, et ce marqueur SHALL être conservé tel quel dans le texte livré et dans celui enregistré.

#### Scenario: Placeholder kept
- **WHEN** l'offre ne contient aucun détail sur l'entreprise
- **THEN** le texte livré contient `[à compléter : détail sur l'entreprise]`
