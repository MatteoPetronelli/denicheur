# Proposal

## Why

La bonne alternance renvoie très peu d'offres de développement (2 retenues sur 16 en fixture). Les grands sites (Indeed, Welcome to the Jungle, LinkedIn, JobTeaser) ne sont accessibles que par les e-mails d'alerte que l'utilisateur reçoit déjà : les lire est la seule voie sans scraping ni contournement. Voir `docs/plans/2026-11-16-denicheur-roadmap.md` §4 C2.

## What Changes

- **L1** — Lecteur IMAP en lecture seule du libellé Gmail `Denicheur` (`BODY.PEEK`, aucun changement de drapeau), testé avec un faux serveur IMAP.
- **L2** — Analyseurs d'e-mails par expéditeur (stdlib `html.parser`), source `email_alertes` qui produit des `Offre` (piste déduite du titre, lien nettoyé des paramètres de suivi, commune géocodée via `api-adresse.data.gouv.fr`), branchement dans `run` quand les identifiants Gmail existent.
- Aucune dépendance ajoutée : `imaplib`, `email`, `html.parser` et `httpx` suffisent.

Hors périmètre : lecture des liens (pas de scraping de pages d'offres), envoi d'e-mails, brouillons Gmail (C5), source Adzuna (C3), bot interactif (C4). Les e-mails ne sont jamais marqués lus ni modifiés.

## Capabilities

### New Capabilities
- `imap-alert-reader`: lecture seule des e-mails d'alerte du libellé Gmail `Denicheur` depuis une date, sans effet de bord sur la boîte.
- `email-alert-source`: extraction des offres des e-mails d'alerte par expéditeur, normalisation en `Offre` (piste, lien propre, lieu géocodé) et collecte tolérante aux e-mails inconnus.

### Modified Capabilities
- `daily-run`: la collecte planifiée inclut la source e-mail lorsque `GMAIL_USER` et `GMAIL_APP_PASSWORD` sont présents ; absents, elle est ignorée sans erreur.

## Impact

- Code : `src/denicheur/mail/` (`imap.py`, `parsers.py`), `src/denicheur/sources/email_alertes.py`, `sources/__init__.py`, `__main__.py` (construction de la source), tests et fixtures `tests/fixtures/emails/*.eml`.
- Dépendances : aucune nouvelle.
- Systèmes : Gmail IMAP (mot de passe d'application), `api-adresse.data.gouv.fr` (gratuit, sans clé). Prérequis humains avant L2 : double authentification Gmail, mot de passe d'application, libellé `Denicheur` avec un filtre sur les expéditeurs d'alertes, 2 à 3 e-mails réels par expéditeur exportés en `.eml` et **anonymisés**.
