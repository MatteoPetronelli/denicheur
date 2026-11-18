# application-documents Specification

## Purpose
Transformer une lettre relue en fichiers prêts à joindre à une candidature (PDF et DOCX modifiable) et fournir le court message d'accompagnement, sans jamais exposer les coordonnées du candidat au modèle de langage.

## Requirements

### Requirement: Letter files
À partir du texte d'une lettre, le service SHALL écrire un fichier PDF et un fichier DOCX contenant : l'en-tête du candidat (nom, adresse, téléphone, e-mail), le lieu et la date du jour, l'objet « Candidature pour le poste de <poste> », le corps de la lettre et la signature. L'en-tête et la signature SHALL venir d'un fichier local et ne SHALL jamais figurer dans un prompt. La ligne « Éléments du profil utilisés » et la note de longueur SHALL être absentes des fichiers.

#### Scenario: Both files written
- **WHEN** une lettre est générée pour une offre
- **THEN** un PDF et un DOCX existent dans le dossier des lettres et contiennent le corps, l'en-tête et la signature

#### Scenario: Review-only lines excluded
- **WHEN** le texte contient la ligne « Éléments du profil utilisés » et la note « ⚠️ longueur hors plage »
- **THEN** ni l'un ni l'autre ne figure dans le PDF ni dans le DOCX

#### Scenario: Project links under the signature
- **WHEN** le texte cite un projet dont l'URL figure dans le fichier local de liens
- **THEN** le lien du projet, puis les profils GitHub et LinkedIn, figurent sous la signature dans le PDF et le DOCX ; un projet non cité n'a pas de lien

#### Scenario: No links file
- **WHEN** le fichier local de liens est absent
- **THEN** les fichiers sont écrits sans lien et sans erreur

#### Scenario: Identity file missing
- **WHEN** le fichier d'identité local est absent
- **THEN** aucun fichier n'est écrit, une erreur explicite en français est levée et aucun détail personnel n'est affiché

### Requirement: File names and folder
Les fichiers SHALL s'appeler « Lettre de motivation <entreprise> » avec l'extension `.pdf` ou `.docx`, dans le dossier des lettres de l'utilisateur. Le nom SHALL être assaini : aucun séparateur de chemin, aucun caractère interdit par Windows, aucun nom vide. Un fichier existant SHALL ne jamais être écrasé : un suffixe « (2) », « (3) »… est ajouté.

#### Scenario: Hostile company name
- **WHEN** le nom d'entreprise contient `..\` ou des caractères interdits
- **THEN** les fichiers sont écrits dans le dossier des lettres, sous un nom sans séparateur de chemin ni caractère interdit

#### Scenario: No overwrite
- **WHEN** un fichier du même nom existe déjà
- **THEN** il est conservé intact et les nouveaux fichiers portent le suffixe « (2) »

#### Scenario: Unknown company
- **WHEN** l'offre n'a pas de nom d'entreprise
- **THEN** le nom du fichier utilise un libellé neutre

### Requirement: Cover message
Le court message d'accompagnement SHALL être un gabarit fixe en français qui cite le poste et l'entreprise, annonce la lettre en pièce jointe et se termine par une formule de politesse et la signature locale. Il ne SHALL jamais être produit par le modèle.

#### Scenario: Template message
- **WHEN** le message d'accompagnement est demandé pour une offre
- **THEN** le texte cite le poste et l'entreprise, sans appel au modèle

### Requirement: No personal data in prompts
Le contenu du fichier d'identité SHALL ne jamais être lu par la rédaction du texte de la lettre ni inclus dans un prompt.

#### Scenario: Identity not in prompt
- **WHEN** un brouillon de lettre est généré avec un fichier d'identité présent
- **THEN** aucun élément du fichier d'identité ne figure dans le prompt

### Requirement: Spontaneous letter files
Pour une candidature spontanée, le service SHALL écrire les mêmes PDF et DOCX, nommés « Lettre de motivation <entreprise> » avec les mêmes règles d'assainissement et de non-écrasement, avec l'objet « Candidature spontanée » au lieu d'un poste. Le message d'accompagnement SHALL être un gabarit fixe, sans appel au modèle, qui parle d'une candidature spontanée et ne cite aucun poste.

#### Scenario: Files for a company
- **WHEN** une lettre est générée pour une entreprise
- **THEN** un PDF et un DOCX « Lettre de motivation <entreprise> » existent et leur objet est « Candidature spontanée »

#### Scenario: Fixed cover message
- **WHEN** le message d'accompagnement d'une entreprise est produit
- **THEN** il mentionne une candidature spontanée, la signature du candidat et aucun poste, et le modèle n'est pas appelé
