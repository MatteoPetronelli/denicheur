"""Compare des modèles Ollama sur des offres étiquetées à la main.

py scripts/compare_modeles.py qwen2.5:7b-instruct mistral llama3.1:8b
py scripts/compare_modeles.py --dry-run
"""

import argparse
import json
from datetime import date
from pathlib import Path

import httpx

from denicheur.config import load_config
from denicheur.scoring.compare import ScorerFactice, comparer
from denicheur.scoring.llm import OllamaScorer

RACINE = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("modeles", nargs="*", help="noms de modèles Ollama")
    p.add_argument("--dry-run", action="store_true", help="scoreur factice, aucun appel Ollama")
    p.add_argument("--etiquettes", default=str(RACINE / "tests" / "fixtures" / "etiquettes.json"))
    args = p.parse_args(argv)
    config = load_config(RACINE / "config" / "recherches.yaml")
    etiquettes = json.loads(Path(args.etiquettes).read_text(encoding="utf-8"))
    today = date.today()

    if args.dry_run:
        candidats = {"factice": ScorerFactice()}
    else:
        if not args.modeles:
            p.error("indique au moins un modèle (ou --dry-run)")
        http = httpx.Client()
        candidats = {}
        for m in args.modeles:
            scoring = config.llm.scoring.model_copy(update={"modele": m})  # seul endroit où le modèle varie
            candidats[m] = OllamaScorer(config.llm.model_copy(update={"scoring": scoring}), http)

    for nom, scorer in candidats.items():
        r = comparer(etiquettes, scorer, today)
        if r["n"] == 0:
            print(f"{nom}: aucune offre étiquetée ({r['ignorees']} sans score_attendu)")
            continue
        print(
            f"{nom}: écart moyen {r['ecart_moyen']:.1f} · seuil 65 franchi à tort : {r['franchissements']}"
            f" · {r['secondes']:.0f} s · {r['n']} offres ({r['ignorees']} ignorées)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
