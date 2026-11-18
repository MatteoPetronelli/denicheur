## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- When graphify-out/graph.json exists, run `graphify query "<question>"` before your first grep, search or source-file read for a codebase question, and put this rule in every subagent prompt that explores code. Read raw files only for lines the graph or an earlier read already located. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
- A committed graphify-out/graph.json is rewritten whole on every build, so a large diff to it in a pull request is expected. Do not flag it as churn or suggest skipping the graph rebuild or its hooks.

## Projet Dénicheur

Outil personnel : collecte offres alternance/stage (La bonne alternance, Adzuna, e-mails d'alerte), scoring LLM, digest Telegram. **Envoi de candidature toujours humain.** Contexte complet : `handoff.md`, `Denicheur-specifications.md`.

- Statut : C0 terminé ; C1 `mvp-alternance-digest` archivé (LBA, filtres, scoring Ollama, Telegram, `run`, tâche planifiée) ; C2 `alertes-email` archivé (Indeed et Jobtome : lecteur IMAP lecture seule, analyseurs, géocodage ; vérifié sur la vraie boîte) ; C3 `source-adzuna-stage` archivé (stages Adzuna, `run --mode stage`) ; C4 `bot-interactif` archivé (suivi des candidatures, bot Telegram en polling, rappel J+7) ; C5 `brouillons-candidature` archivé (e-mail, relance et lettre PDF/DOCX avec `llm.ecriture`, brouillons Gmail par IMAP APPEND, jamais d'envoi ; identité et liens locaux dans `profile/identite.md` et `profile/liens.md`) ; C6 `candidatures-spontanees` archivé (table `entreprises`, import CSV, recruteurs LBA et recherche d'entreprises par département, liste du jour désactivable par `entreprises.liste_par_jour: 0`, boutons `s` `t` `e` `i`, brouillons et lettres d'entreprise plafonnés à 15 par jour) ; C7 `dashboard` en cours (application SvelteKit locale dans `web/`, lue sur la même base : kanban offres et entreprises, entreprises, offres, statistiques, page projet ; lancer avec `cd web && npm run build && npm start`, `http://127.0.0.1:3000`, jamais exposé) ; roadmap `docs/plans/2026-11-16-denicheur-roadmap.md`. Commandes : `init-db`, `import-entreprises <csv>`, `setup-telegram`, `digest [--test]`, `run --mode auto|alternance|stage [--dry-run]`, `bot`. Installation : `py -m pip install -e ".[dev]"`. Gate : `py -m ruff format --check .` · `py -m ruff check .` · `py -m mypy src` · `py -m pytest -q` ; dossier `web/` : `npm run check` · `npm test` · `npm run build` · `npm run e2e`.
- Stack prévue : Python 3.13, httpx, pydantic, SQLAlchemy (SQLite), pytest, ruff. Lancement prévu : `py -m denicheur run`.
- Langue : tout ce que voit l'utilisateur (Telegram, brouillons) en **français** ; code et identifiants en anglais.
- 100 % local et gratuit (décision 2026-11-16) : LLM = **Ollama** (`llama3.1:8b`, modèle et options dans `config/recherches.yaml`), exécution par le Planificateur de tâches Windows, SQLite, bot Telegram en polling. Aucun service payant ni cloud (ni API Anthropic, ni GitHub Actions/Neon/Vercel). Ne jamais changer le modèle ni les options entre requêtes du même type.
- Secrets/données perso : jamais dans git ni envoyés au LLM (`.env`, `identifiants_*.json`, `CV_base/`, `profile/cv_*.md`, `profile/identite.md`, `profile/liens.md`) ; accès à `.env` et `identifiants_*.json` refusé dans `.claude/settings.json` (les règles sur `CV_base/` et `profile/cv_*.md` ont été levées le 2026-11-17 pour C5 ; les remettre si les CV n'ont plus à être lus).
- Workflow : changements via OpenSpec (`/openspec-propose`), un lot à la fois. Pas de code applicatif sans demande explicite.
- Skills projet dans `.claude/skills/` : tdd-workflow, systematic-debugging, mutation-verified-testing, database-design, prompt-engineering, avoid-ai-writing, clean-code, commit, openspec-*.
