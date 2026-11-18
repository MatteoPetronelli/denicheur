import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from denicheur.config import load_config
from denicheur.db import repo
from denicheur.db.base import make_engine, migrer
from denicheur.db.tables import entreprises
from denicheur.entreprises.recherche import (
    ErreurRecherche,
    actualiser,
    actualiser_couple,
    convertir,
    lire_page,
    tranches_entre,
)

RACINE = Path(__file__).parent.parent
CFG = load_config(RACINE / "config" / "recherches.yaml")
TEXTE_FIXTURE = (RACINE / "tests" / "fixtures" / "entreprises_search.json").read_text(encoding="utf-8")
FIXTURE = json.loads(TEXTE_FIXTURE)
NOW = datetime(2026, 11, 18, 9, tzinfo=UTC)
PROCHE = ("48.97", "2.0775")  # environ 10 km au nord du centre
LOIN = ("49.5", "2.0775")  # environ 69 km


@pytest.fixture
def session(tmp_path):
    url = f"sqlite:///{tmp_path / 'test.db'}"
    migrer(url)
    with Session(make_engine(url)) as s:
        yield s


def _etab(siret="12345678900011", coords=PROCHE, etat="A", siege=False, **kw):
    e = {
        "siret": siret, "adresse": "1 RUE X 78000 VERSAILLES", "code_postal": "78000",
        "libelle_commune": "VERSAILLES", "departement": "78", "latitude": coords[0] if coords else None,
        "longitude": coords[1] if coords else None, "etat_administratif": etat, "est_siege": siege,
        "tranche_effectif_salarie": "12",
    }  # fmt: skip
    e.update(kw)
    return e


def _unite(etablissements=None, siege=None, **kw):
    u = {
        "siren": "123456789", "nom_complet": "ACME (ACME)", "activite_principale": "62.02A",
        "tranche_effectif_salarie": "12", "etat_administratif": "A",
        "siege": siege or _etab("12345678900011", LOIN, siege=True),
        "matching_etablissements": etablissements if etablissements is not None else [_etab()],
    }  # fmt: skip
    u.update(kw)
    return u


def _client(pages=None, total_pages=8, statut=200, appels=None):
    def handler(request):
        if appels is not None:
            appels.append(request)
        if statut != 200:
            return httpx.Response(statut, json={"erreur": "x"})
        page = int(request.url.params["page"])
        corps = pages(page) if pages else {"results": [_unite()]}
        return httpx.Response(200, json={"total_results": 100, "page": page, "per_page": 25,
                                         "total_pages": total_pages, **corps})  # fmt: skip

    return httpx.Client(transport=httpx.MockTransport(handler))


def _sleep(_):
    return None


def test_tranches_entre_les_bornes():
    assert tranches_entre(10, 249) == ["11", "12", "21", "22", "31"]
    assert tranches_entre(0, 5) == ["00", "01", "02"]
    assert tranches_entre(250, 499) == ["32"]
    assert tranches_entre(300, 400) == []


def test_etablissement_actif_proche_prefere_au_siege_et_au_ferme():
    ferme = _etab("22222222200022", ("48.90", "2.0775"), etat="F")
    actif = _etab("33333333300033")
    e = convertir(_unite([ferme, actif]), CFG)
    assert e is not None
    assert e.siret == "33333333300033"
    assert e.nom == "ACME (ACME)"
    assert e.adresse == "1 RUE X 78000 VERSAILLES" and e.commune == "VERSAILLES"
    assert (e.lat, e.lon) == (48.97, 2.0775)
    assert e.distance_km == pytest.approx(10.0, abs=0.2)
    assert (e.naf, e.origine, e.priorite) == ("62.02A", "sirene", None)


def test_le_siege_compte_quand_il_est_actif_et_dans_le_rayon():
    siege = _etab("44444444400044", ("48.89", "2.0775"), siege=True)
    e = convertir(_unite([_etab("55555555500055", ("48.95", "2.0775"))], siege=siege), CFG)
    assert e is not None and e.siret == "44444444400044"


def test_aucun_etablissement_actif_dans_le_rayon():
    assert convertir(_unite([_etab(coords=LOIN)]), CFG) is None
    assert convertir(_unite([_etab(etat="F")]), CFG) is None
    assert convertir(_unite([_etab(coords=None)]), CFG) is None
    assert convertir(_unite([_etab(etat=None)]), CFG) is None


def test_rayon_de_la_configuration_applique():
    petit = CFG.model_copy(update={"rayon_km": 5})
    assert convertir(_unite([_etab()]), petit) is None
    assert convertir(_unite([_etab()]), CFG) is not None


def test_libelles_naf_et_effectif_lus_localement():
    e = convertir(_unite(), CFG)
    assert e is not None
    assert e.activite == "Conseil en systèmes et logiciels informatiques"
    assert e.effectif == "20-49"
    inconnu = convertir(_unite(activite_principale="99.99Z", tranche_effectif_salarie="NN"), CFG)
    assert inconnu is not None and inconnu.activite == "99.99Z" and inconnu.effectif is None


def test_donnee_incomplete_donne_none():
    assert convertir(_unite(nom_complet=None), CFG) is None
    assert convertir(_unite([_etab(siret="123")]), CFG) is None
    assert convertir({}, CFG) is None


def test_requete_par_departement_et_naf():
    appels = []
    ent, total, ignorees = lire_page(CFG, _client(appels=appels), "78", "62.02A", 2, _sleep)
    p = appels[0].url.params
    assert appels[0].url.path == "/search"
    assert (p["departement"], p["activite_principale"], p["etat_administratif"]) == ("78", "62.02A", "A")
    assert p["tranche_effectif_salarie"] == "11,12,21,22,31"
    assert (p["per_page"], p["page"]) == ("25", "2")
    assert (len(ent), total, ignorees) == (1, 8, 0)


def test_fixture_reelle_dans_le_rayon_sans_dirigeants():
    assert "dirigeants" not in TEXTE_FIXTURE
    retenues = [e for u in FIXTURE["results"] if (e := convertir(u, CFG))]
    assert len(retenues) >= 5
    assert all(e.distance_km is not None and e.distance_km <= CFG.rayon_km for e in retenues)
    assert len({e.siret[:9] for e in retenues}) == len(retenues)


def test_curseur_avance_de_pages_max_puis_revient_a_la_page_une(session):
    pages = []
    client = _client(pages=lambda p: pages.append(p) or {"results": []}, total_pages=8)
    cle = "curseur_entreprises:78:62.02A"
    actualiser_couple(session, CFG, client, "78", "62.02A", NOW, sleep=_sleep)
    assert (pages, repo.get_param(session, cle)) == ([1, 2, 3], "4")
    pages.clear()
    actualiser_couple(session, CFG, client, "78", "62.02A", NOW, sleep=_sleep)
    assert (pages, repo.get_param(session, cle)) == ([4, 5, 6], "7")
    pages.clear()
    actualiser_couple(session, CFG, client, "78", "62.02A", NOW, sleep=_sleep)
    assert (pages, repo.get_param(session, cle)) == ([7, 8], "1")


def test_curseur_par_couple_independant(session):
    client = _client(pages=lambda p: {"results": []}, total_pages=8)
    actualiser_couple(session, CFG, client, "78", "62.02A", NOW, sleep=_sleep)
    assert repo.get_param(session, "curseur_entreprises:92:62.02A") is None


def test_echec_laisse_le_curseur_inchange_et_leve(session):
    repo.set_param(session, "curseur_entreprises:78:62.02A", "4")
    with pytest.raises(ErreurRecherche):
        actualiser_couple(session, CFG, _client(statut=500), "78", "62.02A", NOW, sleep=_sleep)
    assert repo.get_param(session, "curseur_entreprises:78:62.02A") == "4"


def test_reponse_invalide_leve_sans_detail(session):
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, text="pas du json")))
    with pytest.raises(ErreurRecherche) as e:
        actualiser_couple(session, CFG, client, "78", "62.02A", NOW, sleep=_sleep)
    assert "pas du json" not in str(e.value)


def test_entreprises_enregistrees_et_incompletes_comptees(session):
    pages = {"results": [_unite(), _unite([_etab(coords=LOIN)], siren="999999999"), _unite(nom_complet=None)]}
    client = _client(pages=lambda p: pages, total_pages=1)
    bilan = actualiser_couple(session, CFG, client, "78", "62.02A", NOW, sleep=_sleep)
    session.commit()
    assert (bilan.creees, bilan.ignorees) == (1, 2)
    assert session.execute(select(entreprises.c.siret)).scalars().all() == ["12345678900011"]


def test_aucun_dirigeant_stocke_ni_journalise(session, caplog):
    unite = _unite()
    unite["dirigeants"] = [{"nom": "DUPONTEL", "prenoms": "Zacharie", "date_de_naissance": "1963-11"}]
    client = _client(pages=lambda p: {"results": [unite]}, total_pages=1)
    with caplog.at_level(logging.DEBUG):
        actualiser_couple(session, CFG, client, "78", "62.02A", NOW, sleep=_sleep)
    session.commit()
    ligne = session.execute(text("select * from entreprises")).all()
    assert ligne and "DUPONTEL" not in repr(ligne) and "Zacharie" not in repr(ligne)
    assert "DUPONTEL" not in caplog.text and "1963" not in repr(ligne)


def test_actualiser_s_arrete_au_premier_echec_et_le_consigne(session):
    appels = []
    bilan = actualiser(session, CFG, _client(statut=500, appels=appels), NOW, sleep=_sleep)
    assert len(appels) <= 4  # les tentatives du seul premier couple
    assert len(bilan.erreurs) == 1 and "ErreurRecherche" in bilan.erreurs[0]
    assert "78" in bilan.erreurs[0] and "62.01Z" in bilan.erreurs[0]


def test_actualiser_parcourt_tous_les_couples_et_espace_les_appels(session):
    appels, pauses = [], []
    client = _client(pages=lambda p: {"results": []}, total_pages=1, appels=appels)
    bilan = actualiser(session, CFG, client, NOW, sleep=pauses.append)
    couples = {(r.url.params["departement"], r.url.params["activite_principale"]) for r in appels}
    assert len(couples) == len(CFG.entreprises.departements) * len(CFG.entreprises.naf)
    assert bilan.erreurs == []
    assert len(pauses) == len(appels) and all(p > 0 for p in pauses)
