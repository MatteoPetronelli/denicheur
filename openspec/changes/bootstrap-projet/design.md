## Context

Dépôt sans code applicatif. Voir proposal.md (Why). Interpréteur local : Python 3.13.2 (cible `>=3.12`). Le `.gitignore` couvre déjà `*.db`, `.vercel/`, `web/.svelte-kit/`.

## Goals / Non-Goals

**Goals:** squelette installable, config/secrets validés, profil sans PII, fixture LBA reproductible, gate qualité verte.
**Non-Goals:** collecte, DB, scoring, Telegram (C1+).

## Decisions

- **Layout `src/` + `pyproject.toml`** : ruff `line-length = 110`, `target-version = "py312"`, select `E,F,I,UP,B,SIM` ; pytest `testpaths = ["tests"]`, `pythonpath = ["src"]`. Dev extras : pytest, ruff, mypy.
- **CLI argparse (stdlib)** : sous-commandes stubs imprimant "non implémenté" ; pas de dépendance CLI supplémentaire.
- **Config** : `Config` pydantic v2 chargé depuis YAML (roadmap §3.5), validation (ex. `rayon_km > 0`). `Secrets` lit `os.environ` ; `adzuna_enabled` dérivé de la présence de `ADZUNA_APP_ID`/`ADZUNA_APP_KEY` ; `DATABASE_URL` par défaut `sqlite:///denicheur.db`. Clé optionnelle absente = source désactivée, jamais de crash.
- **Fixture** : `scripts/make_fixture.py` lit `ft_test_results.json` (gitignoré), écrit le premier bloc en `ensure_ascii=False, indent=1`. Seule la sortie est committée (données publiques d'annonces/entreprises).
- **Profil** : `profile/profil.md` = contenu de la spec §2 verbatim, sans contacts ; un test de scan PII le garde.

## Risks / Trade-offs

- [Structure de `ft_test_results.json` différente de l'attendu] → mesurer avant d'écrire le script (16 jobs, 150 recruteurs) ; sinon stop et rapport.
- [Python local 3.13 vs cible 3.12] → pas de syntaxe 3.13 ; ruff `target-version` py312.
- [`profil.md` contenant une PII par erreur] → test de scan + relecture manuelle.

## Migration Plan

Additif uniquement ; rollback = `git revert` du commit de lot.
