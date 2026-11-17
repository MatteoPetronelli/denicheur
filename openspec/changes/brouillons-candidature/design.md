# Design

## Context

État observé (C4 archivé, commit `463328c`) :

- `config/recherches.yaml` contient déjà `llm.ecriture` (`llama3.1:8b`, température 0,7, `num_ctx` 8192, `timeout_s` 300) ; `scoring.llm.OllamaScorer` montre le schéma d'appel à `/api/chat`.
- La table `brouillons` existe (`candidature_id` NOT NULL, `type`, `contenu`, `gmail_draft`, `cree_le`) ; une seule ligne `candidatures` par offre, garde en code.
- `mail/imap.py` est en lecture seule (`BODY.PEEK`) ; aucune écriture IMAP n'existe.
- Le bot est une boucle de polling mono-thread : tout appel long bloque la file (Telegram garde les updates en attente).
- `profile/profil.md` existe (sans coordonnées) ; `regles_ecriture.md`, `lettre_modele.md` et `cv_*.md` n'existent pas encore. Les CV et lettres d'exemple de l'utilisateur sont hors dépôt et `CV_base/` est refusé dans `.claude/settings.json`.

Motivation : voir `proposal.md`. Exigences : voir `specs/`.

## Goals / Non-Goals

**Goals:**
- Un brouillon français relisible en moins de 90 s sur le matériel de l'utilisateur, mesuré et rapporté.
- Aucune donnée personnelle (coordonnées, CV locaux, secrets) dans le prompt, les journaux ou les erreurs.
- Un chemin unique de rédaction pour les quatre types, afin que C6 (spontanées) n'ajoute qu'un bouton.

**Non-Goals:**
- Aucun envoi d'e-mail, aucun destinataire deviné, aucune lecture de la boîte.
- Pas de bouton « Lettre » : le type `lettre` existe dans le service mais n'est relié à aucune interface en C5.
- Pas de validation automatique de la qualité du texte au-delà de la longueur, du marqueur et de la ligne de profil : la relecture reste humaine.
- Pas de file ni de thread pour la rédaction.

## Decisions

**1. Rédaction synchrone dans la boucle du bot.** `b:` répond d'abord `answerCallbackQuery` (« ⏳ Rédaction… »), puis génère dans la boucle. Alternative : thread ou processus séparé, rejetée (état partagé, deuxième connexion SQLite, complexité sans gain pour un seul utilisateur). Conséquence : le bot ne répond plus pendant la rédaction, d'où le plafond de durée ci-dessous. Les updates arrivées entre-temps sont traitées ensuite.

**2. Plafond de durée = `llm.ecriture.timeout_s`, abaissé à 90 s.** Le délai par appel est celui de la configuration, jamais surchargé en code (règle du projet : modèle et options ne changent pas entre requêtes du même type). On abaisse la valeur de 300 à 90 dans `config/recherches.yaml` (changement de délai, pas de modèle ni d'options de génération). Un second essai de longueur peut doubler l'attente : on ne le tente que si le premier a duré moins de 45 s, sinon on livre avec la note ⚠️. À mesurer au Lot 3 ; si 90 s est dépassé en usage normal, on le dit et on ajuste le modèle avec l'utilisateur.

**3. Résultat du service : texte brut assemblé.** `rediger` renvoie `str` (corps, puis éventuelle note ⚠️, puis la ligne « Éléments du profil utilisés : … » en dernier). Le même texte est enregistré dans `brouillons.contenu`. Pour Gmail, une fonction pure retire la ligne de profil et la note avant dépôt. Alternative : renvoyer une structure et stocker les morceaux, rejetée (la table n'a qu'une colonne `contenu`, aucune migration voulue).

**4. Prompt : système stable, utilisateur par offre.** Système = `regles_ecriture.md` + `lettre_modele.md` + `profil.md` concaténés dans cet ordre, sans date ni variable. Utilisateur = type, piste, titre, entreprise, commune, description d'offre bornée, projet à citer (issu du score) et la phrase de disponibilité de la piste. Aucun `cv_*.md`. La signature n'est pas rédigée par le modèle (formule de politesse sans nom) : l'utilisateur ajoute la sienne dans Gmail, ce qui évite d'envoyer un nom ou un contact au LLM. Une garde de test échoue si le prompt contient une adresse e-mail, un numéro de téléphone ou un fragment de `cv_*.md`.

**5. Détail d'entreprise.** Le modèle reçoit l'instruction d'écrire le marqueur littéral quand l'offre ne fournit rien ; le code vérifie seulement qu'un marqueur présent n'est pas altéré (pas de réécriture). Un petit modèle peut quand même inventer un détail : la ligne « Éléments du profil utilisés » et la relecture humaine sont le garde-fou, pas le code (limite assumée).

**6. Longueur : comptage en code.** Mots = séquences séparées par des blancs, ligne de profil et note exclues. Un seul second essai ; on garde le texte le plus proche de la plage. Alternative : boucler jusqu'à réussite, rejetée (temps imprévisible).

**7. Brouillon sur offre sans suivi : suivi `interessante`.** `candidature_id` étant obligatoire, la première demande crée le suivi au statut `interessante` (transition déjà permise, n'affirme pas un envoi). Offre `ignoree` ou à issue finale : refus. Statut déjà plus avancé : inchangé.

**8. Relance : un brouillon `relance`, statut `relancee`.** La relance est possible depuis `candidature_envoyee` seulement ; elle enregistre un brouillon `relance` et marque `relancee`. « Une seule » = au plus une ligne `brouillons` de type `relance` par candidature. Point à confirmer par l'utilisateur : marquer `relancee` à la génération (et non au dépôt Gmail ou à un bouton « Envoyée ») est un choix de simplicité ; l'envoi réel reste humain.

**9. Gmail : `APPEND` seul, même identifiants que la lecture.** `imaplib` (bibliothèque standard), `APPEND` dans le dossier des brouillons (`\Draft`) d'un `email.message.EmailMessage` (UTF-8, `To` absent). Même fabrique IMAP injectable que `lire_alertes`, pour tester avec un faux serveur. Aucun `smtplib` : un test lit les sources du paquet `redaction/` et échoue sur l'importation. Les erreurs ne portent ni identifiant ni mot de passe, comme `ErreurImap`. Le compte de l'utilisateur est en français : le dossier s'appelle « [Gmail]/Brouillons ». On ne le code donc pas en dur : un `LIST` repère le dossier portant l'attribut `\Drafts`, et le faux IMAP des tests porte ce nom français.

**10. Boutons : `b:`, `g:<brouillon_id>`, `l:<offre_id>`.** La regex stricte de `lire_donnee` passe de `[pbrx]` à `[pbrxgl]` ; `g` porte l'id d'un brouillon, `l` celui d'une offre. Même double contrôle chat et auteur que les autres boutons. Le bouton « ✉️ Relance » est ajouté au clavier du rappel J+7 par `pipeline/run.py`.

**11. Lot 1 sans code, supervisé.** Le profil d'écriture est extrait par Claude à partir des fichiers de l'utilisateur, qui relit chaque diff avant enregistrement. Style seulement : aucun nom, adresse ou recruteur recopié. `regles_ecriture.md` et `lettre_modele.md` (génériques, placeholders `{entreprise}`, `{poste}`, `{projet}`, `{detail}`) vont dans git ; `cv_*.md` restent locaux (`.gitignore`).

**12. Lot 4 : fichiers régénérés, pas stockés.** Le bouton `d:<offre_id>` utilise le type `lettre` (250 à 300 mots) et enregistre le texte dans `brouillons.contenu`. Les fichiers ne sont pas référencés en base : le PDF joint au brouillon Gmail est régénéré depuis `contenu` au moment du dépôt. Pas de migration ; en contrepartie, le PDF déposé porte la date du jour du dépôt, pas celle de la génération (acceptable : la lettre est datée au moment où l'utilisateur l'envoie).

**13. Bibliothèques : `fpdf2` et `python-docx`.** Python pur, gratuites, sans service externe ni Word installé. Alternative : convertir un DOCX en PDF avec LibreOffice ou Word, rejetée (dépendance système lourde). Police : une police intégrée à `fpdf2` (Helvetica) ne couvre pas tous les caractères Unicode ; les caractères hors Latin-1 (guillemets typographiques, « œ », tirets longs) sont remplacés avant rendu, et un test le couvre. Un fichier de police TTF peut être ajouté plus tard si besoin.

**14. Identité locale : `profile/identite.md`.** Fichier hors git (règle `.gitignore`), lu seulement par le rendu des fichiers, jamais par `prompts.py`. Format : une ligne par champ (`nom`, `adresse`, `code postal et ville`, `téléphone`, `e-mail`). Absent : erreur explicite sans donnée personnelle. Alternative : lire les `cv_*.md`, rejetée (plus de données, format libre).

**15. Dossier et noms de fichiers.** Dossier par défaut : `lettres motivation taf` sur le Bureau de l'utilisateur, réglable par la variable d'environnement `LETTRES_DIR` (valeur absente de git). Nom : « Lettre de motivation <entreprise> », assaini (séparateurs de chemin, caractères interdits sous Windows, noms réservés, longueur), suffixe « (2) » plutôt que d'écraser. Le bot n'écrit jamais ailleurs que dans ce dossier ; il ne lit pas son contenu.

**16. Court message : gabarit fixe.** Un seul appel au modèle par lettre ; le message d'accompagnement est un texte fixe (poste, entreprise, lettre en pièce jointe, politesse, signature locale). Le CV n'est pas joint automatiquement : l'utilisateur le joint lui-même, ce qui évite de choisir à sa place entre `CV_base/` alternance et stage.

## Risks / Trade-offs

- [PDF ou DOCX illisible ou mal mis en page] → l'utilisateur relit le texte dans Telegram et ouvre le DOCX ; mesure et relecture réelle au Lot 4.
- [Écriture dans un dossier mal configuré] → dossier réglable et vérifié à l'écriture ; un échec produit un message sans chemin et aucun brouillon.

- [Le LLM local invente un détail ou un projet] → ligne « Éléments du profil utilisés », marqueur littéral, relecture humaine avant tout dépôt ; aucune promesse automatique d'exactitude.
- [Rédaction > 90 s ou bot muet pendant l'attente] → plafond de 90 s, second essai conditionné au temps écoulé, mesure au Lot 3 ; message d'échec français si dépassé.
- [Un gros modèle d'écriture décharge le modèle de scoring de la RAM] → `llm.ecriture` reste `llama3.1:8b` par défaut ; tout changement de modèle se fait avec l'utilisateur après relecture de la qualité.
- [Nom du dossier des brouillons dépendant de la langue du compte] → détection par l'attribut `\Drafts` (pas de repli sur un nom codé en dur), erreur sans secret si rien n'est trouvé ; vérifié sur le vrai compte au Lot 3.
- [Double création du brouillon Gmail] → `gmail_draft` vrai bloque une seconde création ; l'indicateur n'est posé qu'après un `APPEND` réussi, donc un échec laisse la reprise possible.
- [Mot de passe d'application exposé] → jamais journalisé ni mis dans une erreur ; httpx déjà en WARNING dans `bot`.

## Open Questions

- Faut-il, après usage réel, un bouton « Lettre » (type déjà prêt dans le service) ? À décider après les premiers brouillons.

## Résultat de la mesure

Mesure réelle du 2026-11-17 (Lot 3, tâche 3.7), `llama3.1:8b`, offre de stage Adzuna, bot lancé par le Planificateur :

- Durée de « ✍️ Brouillon » jusqu'au texte reçu : environ 20 s, estimée par l'utilisateur (objectif < 90 s atteint). Le bot ne journalisait pas la durée à ce moment ; une ligne « rédaction <type> offre <id> : <n> s » existe depuis, pour les mesures suivantes.
- Dépôt Gmail : les deux brouillons de test ont `gmail_draft` vrai en base, donc l'`APPEND` a abouti sur le vrai compte français (dossier repéré par l'attribut `\Drafts`).
- Défauts relevés à la lecture du texte : phrase d'introduction du modèle (« Voici le corps de l'e-mail… ») et reprise de phrases du modèle de lettre qui affirmaient des choses sur l'offre. Corrigés : consigne « texte seul », retrait de la phrase d'introduction en code, modèle de lettre rendu neutre et conditionnel.
