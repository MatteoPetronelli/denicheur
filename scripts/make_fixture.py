"""Écrit le premier bloc de ft_test_results.json dans tests/fixtures/lba_search.json."""

import json
from pathlib import Path

RACINE = Path(__file__).parent.parent


def main() -> None:
    brut = json.loads((RACINE / "ft_test_results.json").read_text(encoding="utf-8"))
    bloc = next(iter(brut.values()))
    cible = RACINE / "tests" / "fixtures" / "lba_search.json"
    cible.write_text(json.dumps(bloc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{cible} : {len(bloc['jobs'])} jobs, {len(bloc['recruiters'])} recruteurs")


if __name__ == "__main__":
    main()
