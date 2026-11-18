# Dénicheur

Assistant personnel de recherche d'**alternance** (priorité) et de **stage**. Il collecte les offres via des sources officielles, les évalue avec un LLM par rapport au profil du candidat et envoie un digest en français sur Telegram. **L'envoi d'une candidature reste toujours une décision humaine.**

> Statut : MVP La bonne alternance en place (collecte, filtres, scoring Ollama, digest et alertes Telegram, tâche planifiée). Alertes e-mail Indeed et Jobtome lues dans Gmail (autres sites : un analyseur par expéditeur dès qu'un e-mail réel existe). Stages collectés via Adzuna (une fois par jour, autour de Marly-le-Roi). Bot Telegram interactif (suivi des candidatures, rappel J+7). Reste à venir : brouillons.

## Fonctionnement

```text
collecte → dédoublonnage → filtres (distance, mots-clés) → scoring LLM → digest Telegram
```

| Élément | Choix |
|---|---|
| Langage | Python 3.13 (httpx, pydantic, SQLAlchemy, pytest, ruff) |
| Données | SQLite locale (`denicheur.db`, migrations Alembic) |
| LLM | Ollama en local, modèle `qwen2.5:14b` (réglages dans `config/recherches.yaml`) |
| Exécution | `py -m denicheur run`, planifié par le Planificateur de tâches Windows |
| Zone | 25 km autour de Mareil-Marly (78) |

## Sources de données

| Source | Usage | Statut |
|---|---|---|
| La bonne alternance (API) | Offres d'alternance et entreprises pour candidature spontanée | Fonctionne |
| Adzuna | Stages (une collecte par jour, `run --mode stage` pour la forcer) | Codé |
| E-mails d'alerte (Indeed, WTTJ, LinkedIn, JobTeaser) via Gmail | Offres des grands sites, sans scraping | Indeed et Jobtome codés ; WTTJ, LinkedIn, JobTeaser à ajouter |
| France Travail (Offres v2, La Bonne Boite v2) | Offres complémentaires | Accès non obtenu |

Aucun scraping de pages protégées, aucun contournement de CAPTCHA, aucun envoi automatique de candidature.

## Configuration

Les secrets se placent uniquement dans un fichier `.env` local, ignoré par git (modèle : `.env.example`).

| Variable | Rôle |
|---|---|
| `LBA_API_KEY` | Clé de l'API La bonne alternance |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Bot Telegram (seul ce `chat_id` est autorisé) |
| `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` | Source stages |
| `GMAIL_USER`, `GMAIL_APP_PASSWORD` | Lecture des alertes et dépôt des brouillons Gmail (mot de passe d'application) |
| `LETTRES_DIR` | Dossier de sortie des lettres (défaut : `lettres motivation taf` sur le Bureau) |
| `DATABASE_URL` | Base de données (défaut `sqlite:///denicheur.db`) |
| `FT_CLIENT_ID`, `FT_CLIENT_SECRET` | France Travail, uniquement si l'accès est accordé |

## Installation et commandes

```bash
py -m pip install -e ".[dev]"
ollama pull llama3.1:8b
py -m denicheur init-db            # crée denicheur.db
py -m denicheur setup-telegram     # affiche le chat.id à copier dans .env
py -m denicheur digest --test      # envoie une offre factice
py -m denicheur run --mode auto    # collecte, filtre, note, notifie (--dry-run : aucun envoi)
py -m denicheur bot                # bot Telegram en polling (boutons et commandes)
powershell -ExecutionPolicy Bypass -File scripts\installer_taches.ps1   # tâches « Denicheur » (collecte) et « DenicheurBot » (bot, à l'ouverture de session)
```

Modes de `run` : `auto` (selon l'heure et l'état en base), `alternance`, `stage`, `digest`. Le paramètre `pause` à `1` en base suspend les envois. Sortie planifiée dans `logs/run.log` (bot : `logs/bot.log`).

Bot Telegram : chaque offre envoyée porte cinq boutons (Je postule, Brouillon, Rappel, Ignorer, Lettre PDF) ; commandes `/aujourdhui /stage /alternance /candidatures /relances /stats /pause /reprendre /config`. Seul ton chat est servi. Sept jours après « Je postule », un rappel part une seule fois, avec un bouton « ✉️ Relance » (une seule relance par candidature). « ✍️ Brouillon » écrit un e-mail en français avec le modèle local ; « 📄 Lettre PDF » écrit la lettre, en PDF et en DOCX dans le dossier des lettres, et envoie les fichiers dans Telegram ; « 📥 Créer le brouillon Gmail » dépose le texte (ou le message d'accompagnement avec le PDF en pièce jointe) dans tes brouillons Gmail. Rien n'est jamais envoyé : l'envoi reste humain.

Candidatures spontanées : `py -m denicheur import-entreprises entreprises_spontanees_mareil-marly.csv` charge ta liste de départ (150 entreprises classées, avec coordonnées) ; le run quotidien ajoute les recruteurs de La bonne alternance et les PME informatiques (10 à 249 salariés, codes NAF 62.01Z, 62.02A, 58.29C, 63.11Z) trouvées par l'API publique « recherche d'entreprises », sans doublon par SIREN. Chaque jour après le digest, une liste de `entreprises.liste_par_jour` entreprises jamais vues part dans Telegram (`0` désactive la liste), une par message, avec quatre boutons : « ✉️ Brouillon spontané », « 📄 Lettre PDF », « ✅ Envoyée » et « ❌ Ignorer ». Au plus 15 brouillons d'entreprise par jour. Une entreprise ayant aussi une offre ouverte (même SIRET) l'indique dans son message. Les brouillons Gmail d'entreprise n'ont pas de destinataire.

Contrôles avant commit : `py -m ruff format --check .` · `py -m ruff check .` · `py -m mypy src` · `py -m pytest -q`.

## Test des API

```bash
export LBA_API_KEY="..."   # voir tableau ci-dessus
py test_france_travail.py   # FT_TEST=offres|lbb|entreprises|alternance pour un seul test
```

## Tableau de bord

Application web locale (SvelteKit, dossier `web/`) qui lit et modifie la même base SQLite que le bot et le run : suivi des offres et des entreprises, statistiques.

> **Ne jamais exposer le port.** Le tableau n'a ni compte ni mot de passe : il écoute uniquement sur `127.0.0.1` et refuse tout autre nom d'hôte. Ne le publie pas, ne redirige pas son port et ne le lance pas sur une autre interface.

Prérequis : Node.js 22 ou plus récent. Premier lancement, puis lancements suivants :

```bash
cd web
npm install        # une seule fois
npm run build      # après chaque mise à jour du code
npm start          # http://127.0.0.1:3000
```

La base est lue dans `../denicheur.db` ; `DB_PATH` indique un autre fichier (`DB_PATH=C:/chemin/denicheur.db npm start`) et `PORT` un autre port. Le tableau ne crée ni ne migre la base : `py -m denicheur init-db` reste la seule façon de créer le schéma. Contrôles du dossier : `npm run check`, `npm test`, et `npm run e2e` (navigateur Chromium, sur une base de démonstration synthétique recréée à chaque fois ; `npx playwright install chromium` la première fois).

Pages : `/` (tableau des candidatures par statut, offres et entreprises ; changement de statut avec les mêmes règles que le bot), `/entreprises` (liste filtrable, « Contactée » et « Écartée »), `/offres` (offres notées, dont celles sous le seuil `score_min` lu dans `config/recherches.yaml` ; `CONFIG_PATH` indique un autre fichier), `/fiche/offre/<id>` et `/fiche/entreprise/<id>` (détails et brouillons en lecture seule). Une candidature marquée ici est marquée partout : les dates `envoyee_le`, `contactee_le` et `ignoree_le` sont posées comme le fait le bot.

## Sécurité et vie privée

- Ne jamais committer : `.env`, `identifiants_*.json`, bases de données, `ft_test_results.json`, `CV_base/`, `profile/cv_*.md`, `profile/identite.md`, `profile/liens.md`.
- Aucune donnée personnelle (téléphone, date de naissance, adresse) n'est envoyée au LLM ni écrite dans les logs.
- Respect des limites des API (La bonne alternance : 60 requêtes/min, usage non lucratif).
- Dépôt à garder **privé**.

## Documentation

- [`Denicheur-specifications.md`](Denicheur-specifications.md) : spécifications complètes.
- [`handoff.md`](handoff.md) : état d'avancement, décisions et prompts de développement.
- [`entreprises_spontanees_mareil-marly.csv`](entreprises_spontanees_mareil-marly.csv) : entreprises IT proches pour candidatures spontanées.
- Workflow de changements : OpenSpec (`openspec/`).

## Installation

```bash
py -m pip install -e ".[dev]"
cp .env.example .env   # puis renseigner les clés ; .env n'est jamais versionné
```

La configuration de recherche est dans `config/recherches.yaml`, le profil envoyé au LLM dans `profile/profil.md` (sans données personnelles), le style d'écriture dans `profile/regles_ecriture.md` et `profile/lettre_modele.md`. Hors git : `profile/identite.md` (en-tête et signature des lettres, jamais lu par le LLM) et `profile/liens.md` (liens GitHub et LinkedIn ajoutés sous la signature).

## Commandes

```bash
py -m denicheur run          # sous-commandes déclarées (run, init-db, stats), pas encore implémentées
py scripts/make_fixture.py   # régénère tests/fixtures/lba_search.json depuis ft_test_results.json
py -m ruff format --check . && py -m ruff check . && py -m mypy src && py -m pytest -q
```

## Alertes e-mail (Gmail)

La source e-mail lit le libellé Gmail `Denicheur` en lecture seule (aucun message modifié ni marqué lu). Prérequis : double authentification Google, mot de passe d'application dans `.env` (`GMAIL_USER`, `GMAIL_APP_PASSWORD`), puis un filtre Gmail qui applique le libellé `Denicheur` aux alertes (Indeed et Jobtome pour l'instant). Sans ces deux variables la source est simplement ignorée.
