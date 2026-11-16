import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from denicheur.config import load_config
from denicheur.models import Piste
from denicheur.sources.adzuna import ErreurAdzuna, collecter

RACINE = Path(__file__).parent.parent
FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "adzuna_search.json").read_text(encoding="utf-8"))
CONFIG = load_config(RACINE / "config" / "recherches.yaml")
NOW = datetime(2026, 11, 16, 9, 0, tzinfo=UTC)
APP_ID, APP_KEY = "id-secret-123", "cle-secrete-456"


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def _renvoie(payload):
    requetes: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requetes.append(request)
        return httpx.Response(200, json=payload)

    return _client(handler), requetes


def _un(titre="Stage développeur web (6 mois)", description="Mission.", **extra):
    return {
        "id": "42",
        "title": titre,
        "description": description,
        "redirect_url": "https://www.adzuna.fr/details/42?utm_medium=api&utm_source=" + APP_ID,
        "created": "2026-11-10T08:30:00Z",
        "latitude": 48.9,
        "longitude": 2.1,
        "company": {"display_name": "ACME"},
        "location": {"display_name": "Marly-le-Roi, Yvelines"},
        **extra,
    }


def _collecter(http, **kw):
    return collecter(CONFIG, http, NOW, APP_ID, APP_KEY, sleep=lambda s: None, **kw)


def test_une_requete_par_mot_cle_avec_les_parametres_attendus():
    http, requetes = _renvoie({"results": []})
    _collecter(http)
    mots = CONFIG.pistes.stage.mots_cles_recherche
    assert len(requetes) == len(mots)
    assert [r.url.params["what"] for r in requetes] == [f"{m} stage" for m in mots]
    p = requetes[0].url.params
    assert p["where"] == CONFIG.pistes.stage.lieu_recherche == "Marly-le-Roi"
    assert p["distance"] == str(CONFIG.rayon_km)
    assert p["max_days_old"] == str(CONFIG.age_max_jours)
    assert p["results_per_page"] == "50"
    assert (p["app_id"], p["app_key"]) == (APP_ID, APP_KEY)


def test_fixture_reelle_normalisee_sans_doublon():
    http, requetes = _renvoie(FIXTURE)
    offres = _collecter(http)
    assert len(requetes) > 1  # la même page revient pour chaque mot-clé
    ids = [o.source_id for o in offres]
    assert len(ids) == len(set(ids)) == len(FIXTURE["results"])
    for o in offres:
        assert o.source == "adzuna" and o.url and o.description and o.titre
        assert o.url.startswith("https://www.adzuna.fr/details/") and "?" not in o.url
        assert "APPID_MASQUE" not in o.url and "utm_" not in o.url
        assert o.lat is not None and o.lon is not None
        assert o.publiee_le and o.publiee_le.utcoffset() == timedelta(0)  # avec fuseau, comme LBA


def test_champs_d_une_offre():
    http, _ = _renvoie({"results": [_un()]})
    o = _collecter(http)[0]
    assert (o.source_id, o.entreprise, o.commune) == ("42", "ACME", "Marly-le-Roi")
    assert o.url == "https://www.adzuna.fr/details/42"
    assert (o.lat, o.lon) == (48.9, 2.1)
    assert o.publiee_le == datetime(2026, 11, 10, 8, 30, tzinfo=UTC)
    assert (o.piste, o.duree_mois) == (Piste.STAGE, 6)


def test_arrondissement_remplace_par_la_commune_suivante():
    http, _ = _renvoie({"results": [_un(location={"display_name": "9ème Arrondissement, Paris"})]})
    assert _collecter(http)[0].commune == "Paris"


def test_coordonnees_absentes_conservees():
    brut = _un()
    del brut["latitude"], brut["longitude"]
    http, _ = _renvoie({"results": [brut]})
    o = _collecter(http)[0]
    assert o.lat is None and o.lon is None


@pytest.mark.parametrize(
    ("titre", "description", "piste"),
    [
        ("Stage développeur", "", Piste.STAGE),
        ("Internship Python", "", Piste.STAGE),
        ("Développeur web", "Un stage de 6 mois", Piste.STAGE),
        ("Développeur web", "Contrat d'alternance", Piste.ALTERNANCE),
        ("Stage ou alternance développeur", "", Piste.STAGE),  # stage d'abord
        ("Alternance développeur", "stage possible", Piste.ALTERNANCE),  # le titre prime sur la description
        ("Développeur web", "CDI", Piste.AUTRE),
    ],
)
def test_piste(titre, description, piste):
    http, _ = _renvoie({"results": [_un(titre=titre, description=description)]})
    assert _collecter(http)[0].piste is piste


@pytest.mark.parametrize(
    ("titre", "description", "duree"),
    [
        ("Stage dev - 6 mois", "", 6),
        ("Stage dev", "durée de 5 mois", 5),
        ("Stage dev (4 mois)", "6 mois", 4),  # le titre prime
        ("Stage dev", "pas de durée", None),
    ],
)
def test_duree(titre, description, duree):
    http, _ = _renvoie({"results": [_un(titre=titre, description=description)]})
    assert _collecter(http)[0].duree_mois == duree


@pytest.mark.parametrize(
    ("texte", "attendu"), [("poste hybride", True), ("télétravail partiel", True), ("sur site", False)]
)
def test_teletravail(texte, attendu):
    http, _ = _renvoie({"results": [_un(description=texte)]})
    assert _collecter(http)[0].teletravail is attendu


@pytest.mark.parametrize("code", [401, 403, 500, 429])
def test_erreur_http_sans_fuite_de_cle(code):
    def handler(request):
        return httpx.Response(code)

    with pytest.raises(ErreurAdzuna) as exc:
        collecter(CONFIG, _client(handler), NOW, APP_ID, APP_KEY, sleep=lambda s: None)
    msg = str(exc.value)
    assert msg == f"HTTP {code}"
    assert APP_ID not in msg and APP_KEY not in msg and "api.adzuna.com" not in msg
    assert exc.value.__cause__ is None and exc.value.__suppress_context__


def test_429_est_reessaye_puis_reussit():
    appels = []

    def handler(request):
        appels.append(1)
        if len(appels) == 1:
            return httpx.Response(429)
        return httpx.Response(200, json={"results": []})

    collecter(CONFIG, _client(handler), NOW, APP_ID, APP_KEY, sleep=lambda s: None)
    assert len(appels) == len(CONFIG.pistes.stage.mots_cles_recherche) + 1


def test_date_avec_decalage_convertie_en_utc():
    http, _ = _renvoie({"results": [_un(created="2026-11-10T10:30:00+02:00")]})
    publiee = _collecter(http)[0].publiee_le
    assert publiee == datetime(2026, 11, 10, 8, 30, tzinfo=UTC)
    assert publiee.utcoffset() == timedelta(0)  # une date +02:00 égale reste +02:00 sans conversion


@pytest.mark.parametrize(("titre", "duree"), [("Stage 12 mois", 12), ("Stage 6mois", 6), ("Stage 3 MOIS", 3)])
def test_duree_formes(titre, duree):
    http, _ = _renvoie({"results": [_un(titre=titre, description="")]})
    assert _collecter(http)[0].duree_mois == duree
