from datetime import date
from typing import Any

from denicheur.models import Offre, ScoreLLM
from denicheur.scoring.llm import Scorer, Usage

SEUIL = 65


class ScorerFactice:
    """Pour `--dry-run` : aucune requête, score constant."""

    def scorer(self, offre: Offre, today: date) -> tuple[ScoreLLM, Usage]:
        s = ScoreLLM(
            score=50, type="alternance", points_forts=[], points_faibles=[], alerte=None,
            projet_a_citer="", resume="",
        )  # fmt: skip
        return s, Usage(0, 0, 0.0)


def comparer(etiquettes: list[dict[str, Any]], scorer: Scorer, today: date) -> dict[str, Any]:
    """Écart moyen, offres qui changent de côté du seuil 65, secondes. Ignore les offres non étiquetées."""
    ecarts, franchissements, secondes, ignorees = [], 0, 0.0, 0
    for e in etiquettes:
        if e["score_attendu"] is None:
            ignorees += 1
            continue
        score, usage = scorer.scorer(Offre.model_validate(e["offre"]), today)
        ecarts.append(abs(score.score - e["score_attendu"]))
        franchissements += (score.score >= SEUIL) != (e["score_attendu"] >= SEUIL)
        secondes += usage.duree_s
    moyen = sum(ecarts) / len(ecarts) if ecarts else 0.0
    return {
        "n": len(ecarts),
        "ecart_moyen": moyen,
        "franchissements": franchissements,
        "secondes": secondes,
        "ignorees": ignorees,
    }
