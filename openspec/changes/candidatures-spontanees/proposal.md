## Why

Le tri des offres ne couvre qu'une partie du marché : beaucoup d'entreprises informatiques proches de Mareil-Marly recrutent sans publier d'annonce. L'utilisateur a déjà une liste de 150 entreprises classées (`entreprises_spontanees_mareil-marly.csv`) mais aucun moyen de la suivre ni d'écrire à chacune sans repartir de zéro. Cette étape en fait une liste du jour dans Telegram, avec le même flux de rédaction que pour les offres. L'envoi reste toujours humain.

## What Changes

- **Table `entreprises`** (migration Alembic) et clé étrangère `candidatures.entreprise_id` : une entreprise suivie a une seule ligne de suivi, comme une offre.
- **Import** de `entreprises_spontanees_mareil-marly.csv` (commande `import-entreprises`, upsert par SIRET, `rang` devient `priorite`) et des recruteurs de La bonne alternance déjà renvoyés par `collecter_recruteurs`.
- **Recherche d'entreprises** : appel à l'API publique `recherche-entreprises.api.gouv.fr` (point d'entrée `near_point`, sans clé, vérifié le 2026-11-18 : réponse 200) pour les codes NAF 62.01Z, 62.02A, 58.29C et 63.11Z, entreprises de moins de 250 salariés, dans le rayon configuré ; upsert par SIRET. Les noms des dirigeants que renvoie l'API ne sont ni stockés ni journalisés.
- **Liste du jour** : une fois par jour, après le digest, 10 entreprises jamais listées ni contactées ni écartées, ordre `priorite` (celles sans priorité à la fin) puis distance, un message par entreprise. Une entreprise n'est jamais listée deux fois.
- **Boutons d'une entreprise** : « ✉️ Brouillon spontané » (`s:<id>`), « 📄 Lettre PDF » (`t:<id>`), « ✅ Envoyée » (`e:<id>`), « ❌ Ignorer » (`i:<id>`). Le message court suit la plage e-mail (120–180 mots, déjà prévue pour `spontanee`) ; la lettre fait 250–300 mots, avec PDF, DOCX et brouillon Gmail comme en C5.
- **Rédaction sans offre** : le prompt parle de l'activité de l'entreprise (nom, activité, commune) sans rien inventer, annonce l'alternance (1 semaine d'école pour 2 en entreprise, dès que possible) et laisse le modèle choisir dans le profil le projet le plus proche de l'activité. Plafond de 15 brouillons par jour pour les entreprises.
- **SIRET des offres** : la source La bonne alternance donne le SIRET de l'employeur de certaines offres ; il est enregistré (colonne `offres.siret`, vide sinon). Une entreprise qui a aussi une offre ouverte n'est jamais écartée de la liste : son message ajoute simplement « 📌 Offre ouverte aussi : <titre> », trouvée par SIRET et jamais par le nom.
- Le brouillon Gmail d'une entreprise n'a pas de destinataire : ni LBA ni l'API ne fournissent d'adresse (vérifié sur la fixture : `recipient_id` et téléphone nuls). L'utilisateur envoie par le formulaire LBA indiqué ou ajoute l'adresse lui-même.

## Capabilities

### New Capabilities
- `prospect-companies`: stockage des entreprises à démarcher (import CSV, recruteurs LBA, recherche d'entreprises), règles de la liste du jour et de non-répétition.

### Modified Capabilities
- `job-storage`: schéma versionné avec la table `entreprises`, un suivi unique par entreprise et le SIRET facultatif d'une offre.
- `lba-source`: le SIRET de l'employeur d'une offre est conservé.
- `application-tracking`: suivi et brouillons d'une entreprise (statuts, `contactee_le`, un brouillon spontané par jour dans la limite de 15).
- `draft-writing`: rédaction `spontanee` et `lettre` à partir d'une entreprise, sans offre ni score.
- `application-documents`: nom du fichier et message d'accompagnement d'une lettre spontanée.
- `gmail-drafts`: sujet du brouillon d'une candidature spontanée.
- `telegram-bot`: boutons `s`, `t`, `e`, `i` d'une entreprise et donnée de bouton étendue.
- `daily-run`: liste du jour envoyée une fois par jour après le digest, actualisation quotidienne des entreprises.
- `cli-entrypoint`: commande `import-entreprises`.

## Impact

- Code : `db/tables.py`, nouvelle migration `migrations/versions/0002_entreprises.py`, `db/repo.py` (entreprises, suivi et brouillons d'une entreprise), nouveau paquet `src/denicheur/entreprises/` (import CSV, recherche d'entreprises, sélection), `redaction/prompts.py` et `service.py` (contexte entreprise), `redaction/documents.py` et `gmail_drafts.py` (noms et sujets), `telegram/keyboard.py`, `bot.py`, `digest.py` ou `run.py` (liste du jour), `messages_fr.py`, `__main__.py`, `config/recherches.yaml` (codes NAF, effectif maximal, taille de la liste, plafond).
- Base : une migration, SQLite en mode WAL inchangé ; aucune donnée personnelle de dirigeant.
- Réseau : un appel quotidien à une API publique gratuite, sans clé ; en cas de panne, la liste du jour utilise ce qui est déjà en base.
- Fichiers locaux : le CSV déjà versionné sert de jeu de départ ; aucun nouveau fichier privé.
- Dépendances : aucune nouvelle (`csv` et `httpx` déjà là).
- Hors périmètre : trouver des adresses e-mail de recruteurs, détecter une réponse, relancer une entreprise (la relance reste réservée aux offres), tableau de bord (C7).
