# Tasks

Gate de chaque lot : `py -m ruff format --check .` · `py -m ruff check .` · `py -m mypy src` · `py -m pytest -q`. Fin de lot : cocher, `graphify update .`, skill `commit` (fichiers nommés, confirmation avant push).

## Lot 1 — Source Adzuna

Skills : `tdd-workflow`, `mutation-verified-testing`. Étape bloquante : un appel réel (script jetable qui charge `.env` sans afficher les clés) enregistre la réponse dans `tests/fixtures/adzuna_search.json`, affiche `count`, 3 titres et les en-têtes de quota éventuels ; vérifier que la réponse ne contient aucun secret avant de commiter.

- [x] 1.1 Capturer la fixture réelle et noter le nombre de résultats, la part de titres en rapport avec le dev et les en-têtes de quota ; constat : l'App ID figure dans `utm_source` des `redirect_url` (la clé secrète n'est nulle part) ; vérifier : la fixture commitée contient `APPID_MASQUE` et ni l'App ID ni la clé
- [x] 1.2 Étendre `PisteStage` avec `lieu_recherche` et `mots_cles_recherche` (au moins 1, au plus 10) et renseigner `config/recherches.yaml` ; vérifier : la configuration charge, 11 mots-clés font échouer le chargement
- [x] 1.3 Extraire de `sources/email_alertes.py` la déduction de piste et le motif de télétravail vers `sources/texte.py` ; vérifier : les tests e-mail existants passent sans modification
- [x] 1.4 Écrire `sources/adzuna.py:collecter` (une requête par mot-clé, normalisation, déduplication par `id`, lien sans `utm_*`, piste titre puis description, durée `N mois`, télétravail, date UTC avec fuseau) ; vérifier avec la fixture et `MockTransport` : nombre de requêtes égal au nombre de mots-clés, aucun `source_id` répété
- [x] 1.5 Gérer les erreurs sans fuite de clé : 401 et 429 persistant lèvent `ErreurAdzuna("HTTP <code>")` ; vérifier : ni la clé ni l'URL dans `str(erreur)`, mutation-vérifier la garde
- [x] 1.6 Mutation-vérifier la piste (ordre titre puis description), la durée et le télétravail
- [x] 1.7 Gate L1 vert (lancer les quatre commandes, noter les chiffres réels)

## Lot 2 — Planification et câblage dans run

Skills : `tdd-workflow`, `mutation-verified-testing`. Étape bloquante : aucune (tests avec fakes) ; la vérification réelle est l'avant-dernière étape.

- [x] 2.1 Ajouter `Deps.sources_stage` (vide par défaut) et factoriser `_collecter` sur une liste de sources et une clé de paramètre ; vérifier : tous les tests de `run` existants passent
- [x] 2.2 Écrire `_stage_due` (mode `stage`, `auto` dans la plage horaire si la date Paris du jour diffère de `derniere_collecte:stage`) ; vérifier : une collecte par jour, forçage hors plage, mode `alternance` sans stage ; mutation-vérifier la comparaison de dates et la plage
- [x] 2.3 Brancher `sources_stage["adzuna"]` dans `__main__._run` seulement si `adzuna_enabled`, avec un client HTTP sans l'en-tête LBA ; vérifier : sans clé `run --dry-run` ne fait aucune requête Adzuna, avec clés la source est appelée en `--mode stage`
- [x] 2.4 Isolation d'erreur : une erreur Adzuna est consignée sans clé et n'empêche ni l'alternance ni le scoring ; vérifier : `executions.erreurs` ne contient que le type d'erreur
- [x] 2.5 Vérification réelle : `py -m denicheur run --mode stage --dry-run` affiche des offres de stage, aucune clé dans la sortie ; noter combien sont retenues et leur score
- [x] 2.6 Gate L2 vert, puis mettre à jour le README (source Adzuna) et la ligne « Statut » de `CLAUDE.md`

## Workflow follow-up

- Archiver le changement (`openspec-archive-change`) une fois le Lot 2 validé.
- Proposer `/compact` tous les deux lots.
