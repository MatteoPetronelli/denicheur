# Design

## Context

C1 est archivé : `run` collecte des sources `(config, now) -> list[Offre]`, dédoublonne, géolocalise, préfiltre, note avec Ollama et notifie. `Secrets` porte déjà `gmail_user` et `gmail_app_password`. Aucun `.eml` n'existe encore dans `tests/fixtures/`. Les contrats viennent de `docs/plans/2026-11-16-denicheur-roadmap.md` §4 C2 et font foi.

Contraintes : 100 % local et gratuit, tests hors réseau (faux IMAP, `MockTransport`), aucune donnée personnelle dans git, prompts ou logs, aucun scraping, aucun envoi d'e-mail.

## Goals / Non-Goals

**Goals:**
- Alimenter le pipeline existant avec les offres des alertes Indeed, WTTJ, LinkedIn et JobTeaser.
- Ne jamais modifier la boîte Gmail de l'utilisateur.

**Non-Goals:**
- Suivre les liens pour récupérer la description complète (scraping de pages protégées exclu).
- Brouillons et envoi Gmail (C5), bot (C4), Adzuna (C3).

## Decisions

1. **Bibliothèque standard seulement** : `imaplib`, `email`, `html.parser`. Alternative écartée : BeautifulSoup ou une bibliothèque IMAP (dépendance pour quelques blocs HTML).
2. **Lecture seule stricte** : `select("Denicheur", readonly=True)`, `UID SEARCH SINCE`, `FETCH (BODY.PEEK[])`. Le test du faux serveur échoue sur toute commande d'écriture (liste blanche des commandes).
3. **Fenêtre glissante sans état** : la source lit les 7 derniers jours à chaque collecte ; le dédoublonnage par URL propre absorbe les recouvrements. Alternative écartée : mémoriser la dernière date en base (état de plus pour un gain nul). Marqué `# shortcut` dans le code.
4. **Un analyseur par expéditeur**, dans un registre indexé par domaine de `From` ; la structure HTML exacte n'est fixée qu'après lecture des `.eml` réels (étape bloquante de L2). Ajouter un site = une fonction et une fixture.
5. **Lien propre** : retrait de `utm_*`, `trk*`, `tracking*`, `refId`, `trackingId` et du fragment ; les paramètres qui identifient l'offre sont conservés. `source_id = sha1(lien propre)`.
6. **Piste par mots du titre**, `autre` sinon ; le préfiltre existant rejette déjà `autre` (`piste_autre`).
7. **Géocodage** via `api-adresse.data.gouv.fr/search/?q=<commune>&type=municipality&limit=1`, cache en mémoire par exécution ; échec réseau ou commune inconnue : coordonnées `None`, ce qui déclenche « lieu à vérifier » dans `appliquer_geo`.
8. **Branchement dans `run`** : `__main__._run` ajoute `sources["email"]` seulement si les deux identifiants existent. La planification de collecte et l'isolation des erreurs de C1 s'appliquent telles quelles ; une authentification refusée est consignée dans `executions.erreurs` sans le mot de passe.
9. **Confidentialité** : l'analyseur ne garde que le bloc de l'offre (titre, entreprise, ville, texte du bloc) ; le texte passe ensuite par `_nettoyer` avant le LLM. Les fixtures sont anonymisées par l'utilisateur avant d'entrer dans git.

## Risks / Trade-offs

- [Descriptions très courtes dans les alertes → score peu discriminant] → le scoring reste neutre faute d'information ; la comparaison de modèles sur des offres issues d'e-mails se fera après L2.
- [Les expéditeurs changent leur HTML] → un test par fixture, un expéditeur cassé ne produit que zéro offre et une ligne de journal, sans arrêter le run.
- [Fixtures `.eml` à anonymiser par l'utilisateur] → étape bloquante explicite ; sans elles L2 ne démarre pas.
- [`api-adresse` indisponible] → repli « lieu à vérifier », jamais d'échec.
- [Doublons entre LBA et e-mails] → clé de dédoublonnage `entreprise|titre|commune` déjà en place.

## Migration Plan

Aucune migration de base. Retour arrière : retirer `GMAIL_APP_PASSWORD` du `.env` désactive la source. Prérequis humains avant L2 : double authentification Gmail, mot de passe d'application, libellé `Denicheur` avec filtre, 2 à 3 `.eml` anonymisés par expéditeur dans `tests/fixtures/emails/`.
