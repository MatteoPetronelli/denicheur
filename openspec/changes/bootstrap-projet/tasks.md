# Tasks

## Lot 1 — Squelette

Skills : `clean-code`, `commit`. Étape bloquante : `py --version` et `git status` (le `.gitignore` couvre déjà `*.db`, `.vercel/`, `web/.svelte-kit/` : ne rien dupliquer).

- [x] 1.1 Créer `pyproject.toml` (projet `denicheur`, `requires-python >=3.12`, src layout, deps runtime, extras `dev`, config ruff/pytest) ; vérifier `py -m pip install -e ".[dev]"` réussit
- [x] 1.2 Créer `src/denicheur/__init__.py` et `__main__.py` (argparse, sous-commandes stubs "non implémenté") ; vérifier `py -m denicheur run` affiche "non implémenté"
- [x] 1.3 Créer `.env.example` (toutes les clés de la roadmap §3.5, valeurs vides) ; vérifier que `.env.example` est suivi par git (`git check-ignore` ne le liste pas)
- [x] 1.4 Écrire `tests/test_smoke.py` (import du paquet + stub CLI) ; vérifier qu'il passe
- [ ] 1.5 Quality gate : `py -m ruff format --check .` · `py -m ruff check .` · `py -m mypy src` · `py -m pytest -q` verts avec chiffres réels ; `graphify update .` ; commit via skill `commit`

## Lot 2 — Config, profil, fixture

Skills : `tdd-workflow`, `mutation-verified-testing` (test de scan PII), `avoid-ai-writing` (README). Étape bloquante : mesurer `ft_test_results.json` (blocs, 16 jobs / 150 recruteurs dans le premier).

- [ ] 2.1 Écrire les tests de config en échec (chargement valide, `rayon_km: -1` rejeté, `adzuna_enabled is False` sans clés, `DATABASE_URL` par défaut) ; vérifier qu'ils échouent pour la bonne raison
- [ ] 2.2 Créer `config/recherches.yaml` (roadmap §3.5) et `src/denicheur/config.py` (`load_config`, `load_secrets`) ; vérifier que les tests de 2.1 passent
- [ ] 2.3 Créer `profile/profil.md` (spec §2, sans contacts) et un test de scan PII (téléphone, `@`, "né le") ; vérifier le test rouge si une PII est injectée puis restaurer (mutation)
- [ ] 2.4 Créer `scripts/make_fixture.py`, l'exécuter une fois, committer `tests/fixtures/lba_search.json` ; vérifier par test : 16 `jobs` et 150 `recruiters`
- [ ] 2.5 Mettre à jour `README.md` en français (installation, `.env`, commandes) ; vérifier que les commandes documentées s'exécutent telles quelles
- [ ] 2.6 Quality gate complet vert avec chiffres réels ; `graphify update .` ; commit via skill `commit`

## Workflow follow-up

- Archiver le change (`openspec-archive-change`) puis mettre à jour les lignes "Statut" et commandes de `CLAUDE.md`.
