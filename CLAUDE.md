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

- Statut : C0 terminé ; C1 `mvp-alternance-digest` codé (LBA, filtres, scoring Ollama, Telegram, `run`, tâche planifiée), vérification réelle et archivage en cours (roadmap `docs/plans/2026-11-16-denicheur-roadmap.md`). Commandes : `init-db`, `setup-telegram`, `digest [--test]`, `run --mode auto [--dry-run]`. Installation : `py -m pip install -e ".[dev]"`. Gate : `py -m ruff format --check .` · `py -m ruff check .` · `py -m mypy src` · `py -m pytest -q`.
- Stack prévue : Python 3.13, httpx, pydantic, SQLAlchemy (SQLite), pytest, ruff. Lancement prévu : `py -m denicheur run`.
- Langue : tout ce que voit l'utilisateur (Telegram, brouillons) en **français** ; code et identifiants en anglais.
- 100 % local et gratuit (décision 2026-11-16) : LLM = **Ollama** (`llama3.1:8b` par défaut, modèle et options dans `config/recherches.yaml`), exécution par le Planificateur de tâches Windows, SQLite, bot Telegram en polling. Aucun service payant ni cloud (ni API Anthropic, ni GitHub Actions/Neon/Vercel). Ne jamais changer le modèle ni les options entre requêtes du même type.
- Secrets/données perso : jamais dans git ni envoyés au LLM (`.env`, `identifiants_*.json`, `CV_base/`, `profile/cv_*.md`) ; accès refusé dans `.claude/settings.json`.
- Workflow : changements via OpenSpec (`/openspec-propose`), un lot à la fois. Pas de code applicatif sans demande explicite.
- Skills projet dans `.claude/skills/` : tdd-workflow, systematic-debugging, mutation-verified-testing, database-design, prompt-engineering, avoid-ai-writing, clean-code, commit, openspec-*.
