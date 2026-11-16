import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from denicheur.config import load_config
from denicheur.models import Piste
from denicheur.sources import SOURCES
from denicheur.sources.la_bonne_alternance import URL, collecter, collecter_recruteurs

RACINE = Path(__file__).parent.parent
FIXTURE = json.loads((RACINE / "tests" / "fixtures" / "lba_search.json").read_text(encoding="utf-8"))
NOW = datetime(2026, 11, 16, 8, tzinfo=UTC)
cfg = load_config(RACINE / "config" / "recherches.yaml")


def _client(avec_cle=True, appels=None):
    def handler(request):
        if appels is not None:
            appels.append(request)
        return httpx.Response(200, json=FIXTURE)

    headers = {"Authorization": "Bearer k"} if avec_cle else {}
    return httpx.Client(transport=httpx.MockTransport(handler), headers=headers)


def test_seize_offres_et_requete():
    appels = []
    offres = collecter(cfg, _client(appels=appels), NOW)
    assert len(offres) == 16
    req = appels[0]
    assert str(req.url).startswith(URL)
    assert req.url.params["romes"] == "M1805,M1806,M1807"
    assert req.url.params["radius"] == "25.0" or req.url.params["radius"] == "25"
    assert req.url.params["latitude"] == "48.88"
    assert req.headers["Authorization"] == "Bearer k"
    assert all(o.piste is Piste.ALTERNANCE and o.source == "lba" for o in offres)


def test_mapping_itic():
    itic = next(o for o in collecter(cfg, _client(), NOW) if o.entreprise == "ITIC PARIS")
    assert itic.lat == pytest.approx(48.8579, abs=1e-3)
    assert itic.lon == pytest.approx(2.3923, abs=1e-3)
    assert itic.debut_des_que_possible is True
    assert itic.debut is None
    assert itic.niveau_diplome == "7"
    assert itic.commune == "Paris"
    assert itic.duree_mois == 6
    assert itic.expire_le == datetime(2027, 1, 12, tzinfo=UTC)


def test_entreprise_absente_donne_none():
    wavestone = [o for o in collecter(cfg, _client(), NOW) if o.commune == "Nanterre"]
    assert wavestone and all(o.entreprise is None for o in wavestone)


def test_entreprise_repli_legal_name_puis_brand():
    data = json.loads(json.dumps(FIXTURE))
    w = data["jobs"][1]["workplace"]
    w["legal_name"], w["brand"] = "LEGAL", "BRAND"
    data["jobs"][2]["workplace"]["brand"] = "BRAND2"
    client = httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=data)),
        headers={"Authorization": "Bearer k"},
    )
    offres = collecter(cfg, client, NOW)
    assert offres[1].entreprise == "LEGAL"
    assert offres[2].entreprise == "BRAND2"


def test_150_recruteurs():
    assert len(collecter_recruteurs(cfg, _client())) == 150


def test_sans_cle_aucun_appel(caplog):
    appels = []
    with caplog.at_level(logging.INFO):
        assert collecter(cfg, _client(avec_cle=False, appels=appels), NOW) == []
    assert appels == [] and "LBA_API_KEY" in caplog.text


def test_registre():
    assert SOURCES["lba"] is collecter


@pytest.mark.parametrize(
    ("remote", "attendu"), [(None, False), ("onsite", False), ("hybrid", True), ("remote", True)]
)
def test_teletravail_selon_remote(remote, attendu):
    data = json.loads(json.dumps(FIXTURE))
    data["jobs"][0]["contract"]["remote"] = remote
    client = httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=data)),
        headers={"Authorization": "Bearer k"},
    )
    assert collecter(cfg, client, NOW)[0].teletravail is attendu


def test_conditions_acces_ajoutees_a_la_description():
    offres = collecter(cfg, _client(), NOW)
    itic = next(o for o in offres if o.entreprise == "ITIC PARIS")
    assert "Conditions d'accès : Cet emploi est accessible avec un niveau Bac+2 à Bac+5" in itic.description
    woodoo = next(o for o in offres if o.entreprise == "SAS WOODOO")
    assert "Conditions d'accès" not in woodoo.description
