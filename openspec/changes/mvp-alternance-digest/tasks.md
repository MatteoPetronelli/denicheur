# Tasks

Gate de chaque lot : `py -m ruff format --check .` · `py -m ruff check .` · `py -m mypy src` · `py -m pytest -q`. Fin de lot : cocher, `graphify update .`, skill `commit` (fichiers nommés, confirmation avant commit). TDD : test rouge pour la bonne raison, puis code minimal.

## Lot 1 — Modèles, base de données, alignement sur le pivot local

Skills : `database-design`, `tdd-workflow`. Étape bloquante : aucune.

- [x] 1.1 Aligner la config sur Ollama : remplacer `llm:` dans `config/recherches.yaml`, `LLMConfig`/`LLMCall` dans `config.py` (`extra="forbid"`), mettre à jour `tests/test_config.py` ; vérifier avec les scénarios « Ollama LLM section » et « Legacy cloud fields rejected »
- [ ] 1.2 Alléger `Secrets` (retirer `anthropic_api_key`, `telegram_webhook_secret`, `dashboard_password`), traiter `DATABASE_URL` vide comme absente, mettre à jour `.env.example` ; vérifier avec les tests « Cloud keys ignored » et « Default database » (code fait ; reste `.env.example` : retirer ANTHROPIC_API_KEY, TELEGRAM_WEBHOOK_SECRET, DASHBOARD_PASSWORD, accès refusé à l'agent)
- [x] 1.3 Retirer `anthropic` et `psycopg` de `pyproject.toml`, ajouter `logs/` à `.gitignore` ; vérifier `py -m pip install -e ".[dev]"` puis `pytest -q`
- [x] 1.4 Écrire `models.py` (`Piste`, `Offre`, `ScoreLLM` avec score 0..100) ; vérifier avec un test de validation (score 120 rejeté)
- [x] 1.5 Écrire `db/base.py` (`make_engine` avec WAL, réécriture des URL postgres), `db/tables.py` (six tables, unicités) ; vérifier avec le test « WAL enabled »
- [x] 1.6 Initialiser Alembic (`alembic.ini`, `migrations/env.py` lisant `DATABASE_URL`), générer et relire à la main la première révision ; vérifier avec un test qui migre une base `tmp_path` et liste les six tables
- [x] 1.7 Écrire `db/repo.py` (insertion idempotente, `urls_connues`, `cles_connues`, `appels_llm_aujourdhui(now)`, `parametres`) et la commande `init-db` ; vérifier avec les tests d'aller-retour offre + score, double insertion, jour Paris, double migration
- [x] 1.8 Gate L1 vert (lancer les quatre commandes, noter les chiffres réels)

## Lot 2 — Source La bonne alternance

Skills : `tdd-workflow`, `mutation-verified-testing`. Étape bloquante : charger la fixture et afficher les valeurs distinctes de `partner_label` et `contract.type` (attendu : `Apprentissage`, `Professionnalisation`) ; si la réalité diffère, arrêter et rapporter.

- [x] 2.1 Écrire `http.py:get_json` (retry 429 avec `Retry-After`, 5xx/timeout avec backoff, 4xx levé, `sleep` injectable) ; vérifier avec les tests 429→200 (sleep appelé avec 1), 401 sans nouvelle tentative, 503 épuisant les tentatives
- [x] 2.2 Écrire `sources/la_bonne_alternance.py` (mapping complet, lon en premier, commune après le code postal, repli du nom d'entreprise) et `sources/__init__.py` (`SOURCES`) ; vérifier avec `MockTransport` : 16 offres, ITIC (`lat≈48.8579`, `lon≈2.3923`, `des_que_possible`, diplôme `"7"`)
- [x] 2.3 Ajouter `collecter_recruteurs` ; vérifier : 150 recruteurs sur la fixture
- [x] 2.4 Gérer la clé `LBA_API_KEY` absente (source ignorée, journal, aucun appel) ; vérifier par test sans appel réseau
- [x] 2.5 Mutation-vérifier la logique de retry et l'ordre lon/lat (casser, voir rouge, restaurer)
- [x] 2.6 Gate L2 vert

## Lot 3 — Dédoublonnage, géo, préfiltre

Skills : `tdd-workflow`, `mutation-verified-testing`. Étape bloquante : exécuter les fonctions du pipeline sur la fixture dans un script jetable et afficher le tableau de la roadmap §0 (16 → 10 → 2) ; si le résultat diffère, arrêter et rapporter.

- [x] 3.1 Écrire `pipeline/normalize.py` (`normaliser_texte`) et `dedupe.py` (`cle_dedup`, `dedupliquer`) ; vérifier : 16 → 10 sur la fixture, paires Wavestone de même clé
- [x] 3.2 Écrire `pipeline/geo.py` (`haversine_km`, `appliquer_geo`) et `config/villes_hors_zone.txt` (~50 villes + Troyes) ; vérifier : Mareil-Marly→Paris 20e = 23,2 ± 0,3 km, offre à 30 km `hors_zone`, coordonnées absentes gardées avec `lieu_a_verifier`, Woodoo vrai, ITIC faux
- [x] 3.3 Écrire `pipeline/prefilter.py` (ordre des motifs, mots entiers) ; vérifier avec `now = 2026-11-16T09:00+01:00` : retenues = ITIC + Woodoo, Capgemini `mot_exclu:confirme`, MGEN `mots_cles_absents`, Wavestone selon le motif mesuré (`trop_ancienne` ou `mots_cles_absents`) ; tout télétravail (`remote` ≠ absent/`onsite`) rejeté avec le motif `teletravail`
- [x] 3.4 Mutation-vérifier la comparaison de rayon, l'exclusion `confirme` et la règle d'âge
- [x] 3.5 Gate L3 vert

## Lot 4 — Scoring LLM (Ollama)

Skills : `prompt-engineering`, `tdd-workflow`, `mutation-verified-testing`. Étape bloquante : `ollama --version` ; `ollama pull qwen2.5:7b-instruct` ; `curl http://localhost:11434/api/tags` liste le modèle ; un appel `/api/chat` de test avec `format` = schéma `ScoreLLM` sur l'offre ITIC, afficher le JSON brut et les secondes. Si `format` est rejeté ou la sortie invalide, arrêter et rapporter.

- [ ] 4.1 Écrire `scoring/prompts.py` (prompt système français stable : rôle, grille 40/20/15/15/10, règles de piste, malus Bac+5 avec alerte, rythme ≠ 1/2 en alerte, bonus `mots_bonus`, `projet_a_citer` parmi les projets du profil ; `user_message(offre, today)` avec description tronquée à 6 000 caractères) ; vérifier : test PII (téléphone, `@`, « né le ») et test de préfixe stable entre deux dates
- [ ] 4.2 Écrire `scoring/llm.py` (`Usage`, `OllamaScorer` avec options lues dans la config) ; vérifier avec `MockTransport` : modèle et options égaux à la config, score 120 rejeté, JSON invalide rejeté
- [ ] 4.3 Écrire `scoring/service.py:scorer_offres` ; vérifier : score stocké avec tokens et secondes, 2e passage sans appel, plafond 1 → un appel, limite de durée, connexion refusée sans crash avec erreur enregistrée
- [ ] 4.4 Mutation-vérifier le cache, le plafond d'appels et la limite de durée
- [ ] 4.5 Écrire `scripts/compare_modeles.py` (`--dry-run` avec le scoreur factice, métriques écart moyen / franchissements de 65 / secondes) ; vérifier en lançant `--dry-run` sur `tests/fixtures/etiquettes.json`
- [ ] 4.6 Étape humaine : l'utilisateur étiquette ~20 offres dans `etiquettes.json` et lance `py scripts/compare_modeles.py qwen2.5:7b-instruct mistral llama3.1:8b` ; figer le modèle de plus petit écart dans `config/recherches.yaml` ; arrêter et consulter l'utilisateur si écart moyen > 15 ou plus de 4 franchissements
- [ ] 4.7 Gate L4 vert

## Lot 5 — Envoi Telegram et messages

Skills : `avoid-ai-writing`, `tdd-workflow`. Étape bloquante : l'utilisateur a créé le bot et renseigné `TELEGRAM_BOT_TOKEN` ; `py -m denicheur setup-telegram` affiche le `chat.id` lu dans `getUpdates`.

- [ ] 5.1 Écrire `telegram/api.py` (`send_message`, `answer_callback`, `edit_keyboard`, `delete_webhook`, `get_updates`, lié à `TELEGRAM_CHAT_ID`, pause d'1 s entre envois) et la commande `setup-telegram` ; vérifier avec `MockTransport` capturant les requêtes (destination = chat configuré)
- [ ] 5.2 Écrire `messages_fr.py:format_offre` (HTML échappé, 3 éléments max par liste, 4096 caractères max, distance, durée/début) ; vérifier : message ITIC égal à la chaîne de référence, `<script>` échappé
- [ ] 5.3 Écrire `telegram/digest.py` et la commande `digest [--test]` ; vérifier : top 10 ≥ 65 par score décroissant, `notifiee_le` posé, digest vide « Rien de nouveau aujourd'hui »
- [ ] 5.4 Relire les textes français avec `avoid-ai-writing` ; vérifier qu'aucun motif listé par le skill ne reste
- [ ] 5.5 Vérification réelle : `py -m denicheur digest --test` livre un message sur le téléphone de l'utilisateur
- [ ] 5.6 Gate L5 vert

## Lot 6 — Commande `run`, exécutions, tâche planifiée

Skills : `tdd-workflow`, `systematic-debugging`. Étape bloquante : `py -m denicheur init-db` crée `denicheur.db` ; `ollama list` montre le modèle retenu.

- [ ] 6.1 Écrire `clock.py` (`paris_now`, `is_daytime`) ; vérifier avec des tests aux bornes 07:00, 08:00, 08:31, 20:00 Paris
- [ ] 6.2 Écrire `pipeline/run.py:executer` (sources dues, isolation des erreurs, stockage de toutes les offres, scoring, ligne `executions`) ; vérifier : une ligne `executions` avec compteurs, pas de recollecte alternance sous 3 h, source en erreur consignée sans arrêt du run
- [ ] 6.3 Ajouter les notifications : alerte « 🚨 Alternance » (score ≥ 80, 08:00–20:00, non répétée au digest), digest une fois par jour dès 08:30, `pause=1` sans envoi, Ollama injoignable avec offres déjà notées envoyées, échec non géré avec message et code 1 ; vérifier : Woodoo 85 à 10:00 alerté une fois, 07:00 sans digest, 08:31 digest unique le même jour
- [ ] 6.4 Mutation-vérifier l'idempotence (envoi unique), la plage horaire et le drapeau `pause`
- [ ] 6.5 Brancher la CLI `run --mode auto|alternance|stage|digest [--dry-run]` ; vérifier : mode invalide refusé, `--dry-run` sans envoi, code de sortie 1 sur échec
- [ ] 6.6 Écrire `scripts/installer_taches.ps1` (tâche `Denicheur`, déclencheur 08:30 répété toutes les heures sur 12 h, `-StartWhenAvailable`, `-MultipleInstances IgnoreNew`, limite 00:30:00, sortie dans `logs/run.log`, remplacement à la réinstallation) ; vérifier : exécuté deux fois, une seule tâche listée
- [ ] 6.7 Test d'invariant : aucun import `smtplib` dans `src/` (grep dans la suite)
- [ ] 6.8 Vérification réelle : `py -m denicheur run --mode auto` produit un digest et une ligne `executions`, puis la tâche planifiée s'exécute seule une fois (voir `logs/run.log`)
- [ ] 6.9 Gate L6 vert, puis mettre à jour le README (installation, `.env`, commandes) et la ligne « Statut » de `CLAUDE.md`

## Workflow follow-up

- Archiver le changement (`openspec-archive-change`) une fois le Lot 6 validé, puis mettre à jour `CLAUDE.md` (Statut, commandes).
- Proposer `/compact` tous les deux lots.
