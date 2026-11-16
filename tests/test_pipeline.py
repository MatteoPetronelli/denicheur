import json
from datetime import datetime, timedelta
from pathlib import Path

import httpx
import pytest

from denicheur.config import load_config
from denicheur.models import Offre, Piste
from denicheur.pipeline.dedupe import cle_dedup, dedupliquer
from denicheur.pipeline.geo import appliquer_geo, haversine_km
from denicheur.pipeline.normalize import normaliser_texte
from denicheur.pipeline.prefilter import prefiltrer
from denicheur.sources.la_bonne_alternance import collecter

RACINE = Path(__file__).parent.parent
FIXTURE = json.loads((RACINE / "tests" / "fixtures" / "lba_search.json").read_text(encoding="utf-8"))
cfg = load_config(RACINE / "config" / "recherches.yaml")
NOW = datetime.fromisoformat("2026-11-16T09:00:00+01:00")


def _offres():
    client = httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=FIXTURE)),
        headers={"Authorization": "Bearer k"},
    )
    return collecter(cfg, client, NOW)


def _traite():
    offres = dedupliquer(_offres(), set(), set())
    return prefiltrer(appliquer_geo(offres, cfg), cfg, NOW)


def _offre(**kw):
    base = {
        "source": "t", "source_id": "1", "url": "u1", "titre": "Développeur Python", "entreprise": "ACME",
        "commune": "Paris", "lat": 48.88, "lon": 2.0775, "piste": Piste.ALTERNANCE, "duree_mois": 12,
        "debut": None, "niveau_diplome": None, "description": "", "publiee_le": NOW - timedelta(days=1),
        "expire_le": None,
    }  # fmt: skip
    return Offre(**{**base, **kw})


# --- normalize / dedupe ---
def test_normaliser_texte():
    assert normaliser_texte("  Développeur   (H/F) – Été ") == "developpeur – ete"
    assert normaliser_texte(None) == ""


def test_cle_identique_malgre_accents_casse_hf():
    a = _offre(titre="Développeur Python H/F", entreprise="Acme")
    b = _offre(titre="DEVELOPPEUR  python", entreprise="ACME", url="u2")
    assert cle_dedup(a) == cle_dedup(b) and len(cle_dedup(a)) == 64


def test_dedupe_fixture_16_vers_10():
    offres = _offres()
    assert len(offres) == 16
    restantes = dedupliquer(offres, set(), set())
    assert len(restantes) == 10
    wave = [o for o in offres if o.entreprise is None]
    assert len({cle_dedup(o) for o in wave}) == 6  # les paires partagent la clé


def test_dedupe_contre_base():
    a, b = _offre(url="u1"), _offre(url="u2", titre="Autre dev")
    assert dedupliquer([a, b], {"u1"}, set()) == [b]
    assert dedupliquer([a, b], set(), {cle_dedup(b)}) == [a]


# --- geo ---
def test_haversine_paris_20e():
    assert haversine_km(cfg.centre.lat, cfg.centre.lon, 48.857929, 2.392314) == pytest.approx(23.2, abs=0.3)


def test_hors_zone_a_30_km():
    # ~30 km à l'est du centre (1° de longitude ≈ 73 km à cette latitude)
    o = appliquer_geo([_offre(lon=cfg.centre.lon + 0.41)], cfg)[0]
    assert 29 < o.distance_km < 31 and o.motif_rejet == "hors_zone"


def test_dans_le_rayon_pas_de_motif():
    o = appliquer_geo([_offre(lon=cfg.centre.lon + 0.20)], cfg)[0]
    assert o.motif_rejet is None and o.distance_km < 25


def test_coordonnees_absentes_gardees_a_verifier():
    o = appliquer_geo([_offre(lat=None, lon=None)], cfg)[0]
    assert o.lieu_a_verifier is True and o.motif_rejet is None and o.distance_km is None


def test_ville_hors_zone_mot_entier():
    assert appliquer_geo([_offre(description="Poste à Troyes.")], cfg)[0].lieu_a_verifier is True
    assert (
        appliquer_geo([_offre(description="Poste à Troyes.", commune="Troyes")], cfg)[0].lieu_a_verifier
        is False
    )
    assert appliquer_geo([_offre(description="Les Troyens")], cfg)[0].lieu_a_verifier is False


# --- prefilter ---
def test_fixture_retenues_exactement_itic_et_woodoo():
    res = _traite()
    assert {o.entreprise for o in res if o.motif_rejet is None} == {"ITIC PARIS", "SAS WOODOO"}
    assert len(res) == 10  # les rejets restent dans le résultat


def test_motifs_mesures_sur_fixture():
    par = {}
    for o in _traite():
        par.setdefault(o.entreprise, []).append(o.motif_rejet)
    assert par["CAPGEMINI"] == ["mot_exclu:confirme"]
    assert par["MUTUELLE GENERALE EDUCATION NATIONALE"] == ["mots_cles_absents"]
    assert sorted(par[None]) == ["mots_cles_absents"] + ["trop_ancienne"] * 5
    assert par["ITIC PARIS"] == [None]


def test_lieu_a_verifier_woodoo_vrai_itic_faux():
    par = {o.entreprise: o for o in _traite()}
    assert par["SAS WOODOO"].lieu_a_verifier is True
    assert par["ITIC PARIS"].lieu_a_verifier is False


@pytest.mark.parametrize(
    ("kw", "motif"),
    [
        ({"piste": Piste.AUTRE}, "piste_autre"),
        ({"expire_le": NOW - timedelta(days=1)}, "expiree"),
        ({"publiee_le": NOW - timedelta(days=31)}, "trop_ancienne"),
        ({"titre": "Développeur Senior"}, "mot_exclu:senior"),
        ({"titre": "Comptable"}, "mots_cles_absents"),
        ({"teletravail": True}, "teletravail"),
    ],
)
def test_motifs_prefiltre(kw, motif):
    assert prefiltrer([_offre(**kw)], cfg, NOW)[0].motif_rejet == motif


def test_age_limite_30_jours_conservee():
    assert prefiltrer([_offre(publiee_le=NOW - timedelta(days=30))], cfg, NOW)[0].motif_rejet is None


def test_ordre_des_regles():
    o = _offre(piste=Piste.AUTRE, titre="Comptable senior", publiee_le=NOW - timedelta(days=90))
    assert prefiltrer([o], cfg, NOW)[0].motif_rejet == "piste_autre"


def test_mot_cle_en_mot_entier():
    # "ia" ne doit pas matcher à l'intérieur de "comptabilite"
    assert prefiltrer([_offre(titre="Comptabilité")], cfg, NOW)[0].motif_rejet == "mots_cles_absents"


def test_teletravail_inclus_si_configure():
    c = cfg.model_copy(update={"inclure_teletravail": True})
    assert prefiltrer([_offre(teletravail=True)], c, NOW)[0].motif_rejet is None


def test_hors_zone_conserve_par_prefiltre():
    o = appliquer_geo([_offre(lon=cfg.centre.lon + 0.41)], cfg)
    assert prefiltrer(o, cfg, NOW)[0].motif_rejet == "hors_zone"
