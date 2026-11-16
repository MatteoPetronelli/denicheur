# Proposal

## Why

Le Dénicheur envoie des offres mais ne sait rien de ce que l'utilisateur en fait : impossible de dire « j'ai postulé », d'écarter une offre ou d'être relancé une semaine après. Il faut pouvoir agir depuis le téléphone, dans Telegram, et suivre les candidatures dans `denicheur.db`. L'envoi d'une candidature reste toujours humain : le bot ne fait que consigner ce que l'utilisateur déclare.

## What Changes

- Modèle de suivi : statuts de candidature, transitions contrôlées, offres à relancer et statistiques (table `candidatures` existante, aucune colonne ajoutée a priori).
- Bot Telegram en long polling (`py -m denicheur bot`) : boutons « Je postule / Brouillon / Rappel / Ignorer » et commandes `/aujourdhui /stage /alternance /candidatures /relances /stats /pause /reprendre /config`. Seul le chat autorisé est servi ; chaque `update_id` est traité une seule fois.
- Les messages d'offre du digest et des alertes portent le clavier de boutons.
- Rappel J+7 envoyé par `run` pour toute candidature envoyée depuis 7 jours, une seule fois.
- Tâche planifiée « à l'ouverture de session » pour le bot, ajoutée à `scripts/installer_taches.ps1`.
- Le bouton « Brouillon » répond « Brouillon disponible à l'étape C5 » tant que C5 n'existe pas.

## Capabilities

### New Capabilities
- `application-tracking`: statuts de candidature, transitions valides, relances dues, statistiques.
- `telegram-bot`: boucle de polling, liste blanche du chat, idempotence des updates, boutons et commandes.

### Modified Capabilities
- `telegram-digest`: les messages d'offre portent un clavier en ligne.
- `daily-run`: étape de rappel J+7 dans `run`.
- `cli-entrypoint`: nouvelle sous-commande `bot`.

## Impact

- Code : `db/repo.py` (suivi), `telegram/bot.py`, `telegram/commands.py`, `telegram/keyboard.py` (nouveaux), `telegram/digest.py`, `pipeline/run.py`, `messages_fr.py`, `__main__.py`, `scripts/installer_taches.ps1`.
- Données : tables `candidatures` et `parametres` (`dernier_update_id`, `pause`) ; pas de migration Alembic tant qu'aucune colonne ne change.
- Sécurité : le bot est le premier point d'entrée externe du projet (modèle de menaces dans `design.md`).
- Dépendances : aucune. Reste 100 % local et gratuit.
