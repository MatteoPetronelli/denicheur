import json
from pathlib import Path

import pytest

from denicheur.config import load_config
from denicheur.entreprises.lba import depuis_recruteurs

RACINE = Path(__file__).parent.parent
CFG = load_config(RACINE / "config" / "recherches.yaml")
RECRUTEURS = json.loads((RACINE / "tests" / "fixtures" / "lba_search.json").read_text(encoding="utf-8"))[
    "recruiters"
]


def _recruteur(naf="62.01Z", size="10-19", siret="12345678900011", coords=(2.0775, 48.88), **w):
    workplace = {
        "siret": siret, "name": "ACME", "size": size,
        "location": {"address": "1 rue X 78000 Versailles", "geopoint": {"coordinates": list(coords)}},
        "domain": {"naf": {"code": naf, "label": "Libellé"}},
    }  # fmt: skip
    workplace.update(w)
    return {"workplace": workplace, "apply": {"url": "https://lba/acme"}}


def _borne_haute(size):
    return int(size.split("-")[1])


def test_fixture_filtree_sur_les_naf_et_la_taille():
    retenues, ecartees = depuis_recruteurs(RECRUTEURS, CFG)
    attendu = [
        r for r in RECRUTEURS
        if r["workplace"]["domain"]["naf"]["code"] in CFG.entreprises.naf
        and _borne_haute(r["workplace"]["size"]) <= CFG.entreprises.effectif_max
    ]  # fmt: skip
    assert len(retenues) == len(attendu) > 90
    assert len(retenues) + ecartees == 150
    assert {e.siret for e in retenues} == {r["workplace"]["siret"] for r in attendu}
    assert all(e.origine == "lba" and e.priorite is None and e.naf in CFG.entreprises.naf for e in retenues)


def test_champs_converts():
    (e,), _ = depuis_recruteurs([_recruteur(size="3-5")], CFG)
    assert (e.nom, e.naf, e.effectif, e.url_candidature) == ("ACME", "62.01Z", "3-5", "https://lba/acme")
    assert e.activite == "Libellé"
    assert e.commune == "Versailles"
    assert e.adresse == "1 rue X 78000 Versailles"
    assert (e.lat, e.lon) == (48.88, 2.0775)
    assert e.distance_km == pytest.approx(0.0, abs=0.01)


def test_distance_depuis_le_centre_configure():
    (e,), _ = depuis_recruteurs([_recruteur(coords=(2.0775, 48.97))], CFG)  # ~10 km au nord
    assert e.distance_km == pytest.approx(10.0, abs=0.2)


@pytest.mark.parametrize(("size", "garde"), [("200-249", True), ("250-499", False), ("1000-1999", False)])
def test_taille_maximale(size, garde):
    retenues, ecartees = depuis_recruteurs([_recruteur(size=size)], CFG)
    assert (len(retenues), ecartees) == (int(garde), int(not garde))


def test_taille_inconnue_conservee():
    retenues, _ = depuis_recruteurs([_recruteur(size=None)], CFG)
    assert len(retenues) == 1


def test_naf_hors_perimetre_ecarte():
    retenues, ecartees = depuis_recruteurs([_recruteur(naf="62.03Z"), _recruteur(naf="63.11Z")], CFG)
    assert [e.naf for e in retenues] == ["63.11Z"] and ecartees == 1


@pytest.mark.parametrize("mauvais", ["123", None, "1234567890001A"])
def test_siret_invalide_ecarte_et_compte(mauvais):
    retenues, ecartees = depuis_recruteurs([_recruteur(siret=mauvais)], CFG)
    assert (retenues, ecartees) == ([], 1)


def test_sans_nom_ni_position_ecarte():
    sans_nom = _recruteur(name=None)
    sans_position = _recruteur(siret="22222222200022")
    sans_position["workplace"]["location"]["geopoint"] = None
    retenues, ecartees = depuis_recruteurs([sans_nom, sans_position], CFG)
    assert (retenues, ecartees) == ([], 2)


def test_nom_de_repli_raison_sociale_puis_marque():
    r1 = _recruteur(name=None, legal_name="LEGAL", brand="BRAND")
    r2 = _recruteur(siret="22222222200022", name=None, brand="BRAND")
    retenues, _ = depuis_recruteurs([r1, r2], CFG)
    assert [e.nom for e in retenues] == ["LEGAL", "BRAND"]
