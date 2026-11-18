import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from denicheur.config import load_config
from denicheur.db.base import make_engine, migrer
from denicheur.db.tables import entreprises
from denicheur.entreprises.service import actualiser_entreprises

RACINE = Path(__file__).parent.parent
CFG = load_config(RACINE / "config" / "recherches.yaml")
RECRUTEURS = json.loads((RACINE / "tests" / "fixtures" / "lba_search.json").read_text(encoding="utf-8"))[
    "recruiters"
]
RECHERCHE = json.loads(
    (RACINE / "tests" / "fixtures" / "entreprises_search.json").read_text(encoding="utf-8")
)
NOW = datetime(2026, 11, 18, 9, tzinfo=UTC)


@pytest.fixture
def session(tmp_path):
    url = f"sqlite:///{tmp_path / 'test.db'}"
    migrer(url)
    with Session(make_engine(url)) as s:
        yield s


def _api(statut=200):
    def handler(request):
        if statut != 200:
            return httpx.Response(statut, json={})
        return httpx.Response(200, json={**RECHERCHE, "total_pages": 1})

    return httpx.Client(transport=httpx.MockTransport(handler))


def _origines(session):
    return set(session.execute(select(entreprises.c.origine)).scalars())


def test_les_deux_sources_alimentent_la_table(session):
    erreurs = actualiser_entreprises(session, CFG, NOW, lambda: RECRUTEURS, _api(), sleep=lambda s: None)
    assert erreurs == []
    assert _origines(session) == {"lba", "sirene"}


def test_lba_en_panne_n_empeche_pas_la_recherche(session):
    def casse():
        raise httpx.ConnectError("secret-hote")

    erreurs = actualiser_entreprises(session, CFG, NOW, casse, _api(), sleep=lambda s: None)
    assert erreurs == ["entreprises lba : ConnectError"]
    assert _origines(session) == {"sirene"}


def test_recherche_en_panne_garde_les_recruteurs(session):
    erreurs = actualiser_entreprises(session, CFG, NOW, lambda: RECRUTEURS, _api(500), sleep=lambda s: None)
    assert len(erreurs) == 1 and "ErreurRecherche" in erreurs[0]
    assert _origines(session) == {"lba"}


def test_sans_source_lba_pas_d_erreur(session):
    erreurs = actualiser_entreprises(session, CFG, NOW, None, _api(), sleep=lambda s: None)
    assert erreurs == [] and _origines(session) == {"sirene"}


def test_deuxieme_actualisation_ne_duplique_rien(session):
    for _ in range(2):
        actualiser_entreprises(session, CFG, NOW, lambda: RECRUTEURS, _api(), sleep=lambda s: None)
    sirets = session.execute(select(entreprises.c.siret)).scalars().all()
    assert len(sirets) == len(set(sirets)) == len({s[:9] for s in sirets})
