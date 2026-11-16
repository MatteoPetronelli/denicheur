import pytest
from pydantic import ValidationError

from denicheur.models import Offre, Piste, ScoreLLM


def _score(**kw):
    base = {
        "score": 80,
        "type": "alternance",
        "points_forts": ["a"],
        "points_faibles": [],
        "alerte": None,
        "projet_a_citer": "p",
        "resume": "r",
    }
    return ScoreLLM(**{**base, **kw})


@pytest.mark.parametrize("valeur", [-1, 101, 120])
def test_score_hors_bornes_rejete(valeur):
    with pytest.raises(ValidationError):
        _score(score=valeur)


def test_score_bornes_ok():
    assert _score(score=0).score == 0
    assert _score(score=100).score == 100


def test_offre_valeurs_par_defaut():
    o = Offre(
        source="lba", source_id="1", url="u", titre="t", entreprise=None, commune=None,
        lat=None, lon=None, piste=Piste.ALTERNANCE, duree_mois=None, debut=None,
        niveau_diplome=None, description="", publiee_le=None, expire_le=None,
    )  # fmt: skip
    assert o.lieu_a_verifier is False and o.motif_rejet is None and o.distance_km is None
