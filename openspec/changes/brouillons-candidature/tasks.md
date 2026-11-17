# Tasks

## 1. Lot 1 : profil d'écriture (supervisé, sans code ; skill : avoid-ai-writing)

- [x] 1.1 Étape bloquante : l'utilisateur autorise la lecture de `CV_base/` (refusée dans `.claude/settings.json`) et relance Claude avec `--add-dir "C:\Users\era92\Desktop\Matteo\lettres motivation taf"`. Vérifié quand les deux dossiers se listent sans refus.
- [x] 1.2 Extraire `profile/cv_alternance.md` et `profile/cv_stage.md` des deux CV (titre « Recherche d'alternance » avec rythme 1 semaine école / 2 semaines entreprise et disponibilité immédiate ; « Recherche de stage 5–6 mois, janvier/février 2027 »), rien d'inventé. Vérifié : diff montré et validé par l'utilisateur, `git status` ne liste aucun `profile/cv_*.md`, `.gitignore` contient `profile/cv_*.md`.
- [x] 1.3 Écrire `profile/regles_ecriture.md` (ton, vouvoiement, longueurs, interdits, détail inconnu = marqueur littéral, ligne « Éléments du profil utilisés ») et `profile/lettre_modele.md` (placeholders `{entreprise}`, `{poste}`, `{projet}`, `{detail}`) à partir du style des lettres d'exemple. Vérifié : diff validé par l'utilisateur, aucun nom d'entreprise, adresse ou recruteur recopié (relecture par recherche des noms propres de l'exemple), passage du skill `avoid-ai-writing`.

## 2. Lot 2 : service de rédaction (skills : prompt-engineering, avoid-ai-writing, tdd-workflow, mutation-verified-testing)

- [ ] 2.1 `redaction/prompts.py` : message système (règles + modèle de lettre + profil, stable) et message utilisateur (type, offre, projet à citer, disponibilité de la piste). Vérifié par tests : système identique d'un appel à l'autre, aucun fragment de `cv_*.md`, adresse ou téléphone dans le prompt (mutation : concaténer un `cv_*.md` → test rouge), fichier de profil absent → erreur française sans appel.
- [ ] 2.2 `redaction/service.py` : `rediger(offre, score, type)` avec `llm.ecriture` de la configuration, type inconnu refusé, `OllamaIndisponible` et réponse inutilisable convertis en erreur dédiée. Vérifié par tests avec transport factice (corps de requête = options de la config, Ollama arrêté, délai dépassé).
- [ ] 2.3 Contrôle de longueur : e-mail 120–180 mots, lettre 250–300, un seul second essai (seulement si le premier a duré moins de 45 s), meilleur texte livré avec la note « ⚠️ longueur hors plage ». Vérifié par tests : dans la plage = 1 appel, 90 puis 140 mots = texte du second, deux échecs = pas de troisième appel ; mutation : retirer la limite d'un essai → rouge.
- [ ] 2.4 Ligne « Éléments du profil utilisés » conservée en dernier ou ajoutée si absente ; marqueur `[à compléter : détail sur l'entreprise]` conservé tel quel. Vérifié par tests (ligne présente, absente, marqueur intact dans le texte livré).
- [ ] 2.5 Abaisser `llm.ecriture.timeout_s` de 300 à 90 dans `config/recherches.yaml` sans toucher au modèle ni aux autres options. Vérifié par `load_config` et le test d'options.
- [ ] 2.6 Gate complète verte (`ruff format --check`, `ruff check`, `mypy src`, `pytest -q`) et `graphify update .`. Vérifié par les comptes affichés.

## 3. Lot 3 : branchement Telegram et brouillons Gmail (skills : tdd-workflow, mutation-verified-testing, threat-modeling)

- [ ] 3.1 `db/repo.py` : enregistrer un brouillon, lire un brouillon, marquer déposé, compter les relances ; brouillon sur offre sans suivi crée `interessante`, refus sur `ignoree` ou issue finale ; relance depuis `candidature_envoyee` seulement, marque `relancee`, une seule. Vérifié par `tests/test_tracking.py` complétés (statut inchangé si déjà avancé, base inchangée après refus) et mutation : retirer la limite à une relance → rouge.
- [ ] 3.2 `redaction/gmail_drafts.py` : `creer_brouillon(user, password, sujet, corps, a="", imap_factory)` par `APPEND` dans le dossier portant l'attribut `\Drafts` (« [Gmail]/Brouillons » sur ce compte français, repéré par `LIST`), drapeau `\Draft`, `EmailMessage` UTF-8, erreurs sans secret, connexion toujours fermée ; fonction pure qui retire la ligne de profil et la note. Vérifié par tests avec faux IMAP : exactement un `APPEND` dans le dossier français, dossier introuvable = erreur sans `APPEND`, aucun `To` inventé, accents intacts, connexion refusée et `APPEND` refusé sans secret dans l'erreur.
- [ ] 3.3 Invariant : le paquet `redaction/` n'importe jamais `smtplib` et n'ouvre aucune connexion SMTP. Vérifié par un test qui lit les sources ; mutation : ajouter `import smtplib` → rouge.
- [ ] 3.4 `telegram/keyboard.py` : actions `g` et `l` admises dans `lire_donnee`, clavier du brouillon (bouton « 📥 Créer le brouillon Gmail »), clavier du rappel avec « ✉️ Relance ». Vérifié par tests de forme (données ≤ 64 octets) et rejets (`g:abc`, `z:1`) ; mutation : élargir la regex → rouge.
- [ ] 3.5 `telegram/bot.py` et `messages_fr.py` : `b:` répond « ⏳ Rédaction… », génère, enregistre, envoie le texte et le bouton ; `g:` dépose une seule fois et répond ; `l:` génère la relance ou refuse la seconde sans appel au modèle ; échec de rédaction ou de Gmail = message français sans secret et boucle intacte. Vérifié par tests de la boucle (chat étranger = 0 appel, doublon, Ollama arrêté, Gmail indisponible, second `g:` sans second `APPEND`).
- [ ] 3.6 `pipeline/run.py` : le rappel J+7 porte le clavier « ✉️ Relance ». Vérifié par test sur le corps de requête du rappel.
- [ ] 3.7 Mesure réelle avec l'utilisateur : « ✍️ Brouillon » sur une offre réelle, durée mesurée et rapportée (objectif < 90 s), brouillon relu par l'utilisateur, un dépôt Gmail vérifié dans la boîte. Vérifié par le temps consigné dans `design.md`, section « Résultat de la mesure ».
- [ ] 3.8 Gate complète verte, `openspec validate brouillons-candidature --strict`, `graphify update .`.

## 4. Clôture

- [ ] 4.1 Mettre à jour `README.md` (boutons Brouillon et Relance, dépôt Gmail, profil d'écriture) et `CLAUDE.md` (statut C5). Vérifié par relecture.
- [ ] 4.2 Archiver avec `openspec archive brouillons-candidature --yes` ; écrire les Purpose des nouvelles specs si le placeholder « TBD » apparaît ; `openspec validate --specs --strict` vert.

## Workflow follow-up

- Prérequis humain avant 1.1 : autoriser l'accès aux CV et au dossier des lettres ; relire chaque diff du Lot 1.
- Prérequis humain avant 3.7 : bot lancé, Ollama actif, mot de passe d'application Gmail dans `.env` ; ne jamais lancer deux bots en même temps.
- Un lot à la fois ; commits Conventional Commits sans trailer IA ; demander avant de pousser.
