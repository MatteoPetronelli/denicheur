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

- Statut : phase de cadrage, **aucun code applicatif** encore (roadmap P0→P6 dans `handoff.md` §9). Pas de commandes build/test vérifiées : à ajouter ici après P0.
- Stack prévue : Python 3.12, httpx, pydantic, SQLAlchemy (SQLite puis Postgres), pytest, ruff. Lancement prévu : `py -m denicheur run`.
- Langue : tout ce que voit l'utilisateur (Telegram, brouillons) en **français** ; code et identifiants en anglais.
- LLM : `claude-sonnet-5-5`, effort `low` pour le scoring, `medium` pour l'écriture ; ne jamais changer l'effort entre requêtes du même type.
- Secrets/données perso : jamais dans git ni envoyés au LLM (`.env`, `identifiants_*.json`, `CV_base/`, `profile/cv_*.md`) ; accès refusé dans `.claude/settings.json`.
- Workflow : changements via OpenSpec (`/openspec-propose`), un lot à la fois. Pas de code applicatif sans demande explicite.
- Skills projet dans `.claude/skills/` : tdd-workflow, systematic-debugging, mutation-verified-testing, database-design, prompt-engineering, avoid-ai-writing, clean-code, commit, openspec-*.
