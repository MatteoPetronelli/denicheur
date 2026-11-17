## Why

Le bouton « ✍️ Brouillon » des offres répond encore « Brouillon disponible à l'étape C5 », et le rappel J+7 n'offre aucun moyen de relancer. Écrire chaque candidature à la main est le goulot qui reste après le tri des offres. Cette étape produit, en local avec Ollama, un brouillon français relu dans Telegram, puis le dépose au besoin dans les brouillons Gmail. L'envoi reste toujours humain.

## What Changes

- Nouveau service de rédaction : `rediger(offre, score, type)` pour les types `email`, `lettre`, `relance`, `spontanee`, avec le modèle et les options de `llm.ecriture` (déjà présents dans `config/recherches.yaml`, jamais surchargés).
- Le prompt système est stable : `profile/regles_ecriture.md` + `profile/lettre_modele.md` + `profile/profil.md`. Les `profile/cv_*.md` (coordonnées) et tout identifiant ne sont jamais envoyés au LLM.
- Chaque brouillon se termine par une ligne « Éléments du profil utilisés : … ». Longueurs : e-mail 120–180 mots, lettre 250–300 ; un second essai si hors plage, puis envoi tel quel (la longueur n'est que journalisée). Texte toujours complet et prêt à envoyer : aucun trou à compléter, rien d'inventé sur l'entreprise.
- Bot : « ✍️ Brouillon » (`b:`) répond « ⏳ Rédaction… », génère, enregistre dans `brouillons`, renvoie le texte avec un bouton « 📥 Créer le brouillon Gmail » (`g:<brouillon_id>`). Le plafond de durée du LLM protège la boucle de polling.
- Création d'un brouillon Gmail par IMAP `APPEND "[Gmail]/Drafts"` avec le drapeau `\Draft`, sans destinataire inventé, jamais d'envoi, aucun `smtplib`.
- Le message de rappel J+7 reçoit un bouton « ✉️ Relance » (`l:<offre_id>`) ; une seule relance par candidature, la seconde demande est refusée avec un message.
- **Lot 4 : lettre en PDF et DOCX.** Un bouton « 📄 Lettre PDF » (`d:<offre_id>`) génère la lettre (250–300 mots), l'enregistre, écrit un PDF et un DOCX dans le dossier des lettres de l'utilisateur, les envoie dans Telegram et propose le dépôt Gmail avec le PDF en pièce jointe et un court message d'accompagnement. L'en-tête et la signature viennent d'un fichier local ajouté par le code, jamais envoyé au LLM ; le court message est un gabarit fixe, sans appel au modèle.
- **Lot 1 sans code, supervisé** : écrire `profile/regles_ecriture.md` et `profile/lettre_modele.md` (génériques, versionnés) et les `profile/cv_*.md` (locaux, hors git) à partir des CV et des lettres d'exemple de l'utilisateur.

## Capabilities

### New Capabilities
- `draft-writing`: génération des brouillons français (types, prompt stable, contrôle de longueur, ligne de profil, texte sans trou à compléter, absence de données personnelles dans le prompt).
- `gmail-drafts`: dépôt d'un texte dans les brouillons Gmail par IMAP, sans aucun envoi.
- `application-documents`: lettre de motivation en PDF et DOCX (en-tête et signature locaux, fichiers nommés sans écrasement) et court message d'accompagnement.

### Modified Capabilities
- `telegram-bot`: le bouton « Brouillon » génère et enregistre un brouillon ; nouveaux boutons « Créer le brouillon Gmail », « Relance » et « Lettre PDF » ; actions `g`, `l` et `d` admises dans la donnée des boutons ; envoi de fichiers dans le chat.
- `daily-run`: le message de rappel J+7 porte le bouton « ✉️ Relance ».
- `application-tracking`: demander un brouillon sur une offre sans suivi crée le suivi `interessante` ; une relance marque `relancee` et n'est possible qu'une fois.

## Impact

- Code : nouveau paquet `src/denicheur/redaction/` (`prompts.py`, `service.py`, `gmail_drafts.py`) ; `telegram/keyboard.py` (regex et claviers), `telegram/bot.py`, `messages_fr.py`, `pipeline/run.py` (clavier du rappel), `db/repo.py` (brouillons).
- Base : table `brouillons` déjà créée (C1) ; aucune migration prévue.
- Fichiers locaux : `profile/regles_ecriture.md`, `profile/lettre_modele.md` (git), `profile/cv_alternance.md`, `profile/cv_stage.md` (hors git, vérifier `.gitignore`).
- Dépendances : `imaplib` et `email` de la bibliothèque standard pour Gmail ; Lot 4 : `fpdf2` (PDF) et `python-docx` (DOCX), Python pur, gratuits, sans service externe.
- Fichiers locaux du Lot 4 : `profile/liens.md` (liens GitHub et LinkedIn ajoutés sous la signature, comme dans les lettres d'origine ; hors git) et `profile/identite.md` (nom, adresse, téléphone, e-mail ; hors git, jamais lu par le LLM) et le dossier de sortie des lettres, par défaut `lettres motivation taf` sur le Bureau, réglable par une variable d'environnement.
- Étape bloquante du Lot 1 : l'utilisateur autorise la lecture de `CV_base/` et du dossier des lettres.
- Sécurité : aucun secret ni coordonnée dans le prompt, les journaux ou les erreurs ; le mot de passe d'application Gmail déjà en `.env` sert à l'APPEND.
