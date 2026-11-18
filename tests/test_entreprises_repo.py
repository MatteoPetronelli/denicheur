from datetime import UTC, datetime

import pytest
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from denicheur.db import repo
from denicheur.db.base import make_engine, migrer
from denicheur.db.tables import entreprises
from denicheur.models import Entreprise

T1 = datetime(2026, 11, 18, 9, tzinfo=UTC)
T2 = datetime(2026, 11, 19, 9, tzinfo=UTC)


@pytest.fixture
def session(tmp_path):
    url = f"sqlite:///{tmp_path / 'test.db'}"
    migrer(url)
    with Session(make_engine(url)) as s:
        yield s


def _e(**kw):
    base = {"siret": "12345678900011", "nom": "ACME", "origine": "csv"}
    return Entreprise(**{**base, **kw})


def _ligne(session, eid=1):
    return session.execute(select(entreprises).where(entreprises.c.id == eid)).mappings().one()


def test_creation_puis_relecture(session):
    e = _e(
        activite="Edition de logiciels", naf="58.29C", effectif="10-19", adresse="1 rue X 78000 Y",
        commune="Y", lat=48.9, lon=2.1, distance_km=4.7, priorite=3, url_candidature="https://lba/x",
    )  # fmt: skip
    eid, cree = repo.enregistrer_entreprise(session, e, T1)
    session.commit()
    assert cree is True
    assert repo.lire_entreprise(session, eid) == e


def test_meme_siret_une_seule_ligne_et_champs_mis_a_jour(session):
    a, cree_a = repo.enregistrer_entreprise(session, _e(), T1)
    b, cree_b = repo.enregistrer_entreprise(session, _e(nom="ACME SAS", commune="Paris"), T2)
    session.commit()
    assert (a, cree_a, b, cree_b) == (1, True, 1, False)
    assert session.execute(select(entreprises.c.id)).all() == [(1,)]
    lue = repo.lire_entreprise(session, 1)
    assert (lue.nom, lue.commune) == ("ACME SAS", "Paris")
    ligne = _ligne(session)
    assert ligne["cree_le"] == T1.replace(tzinfo=None)
    assert ligne["maj_le"] == T2.replace(tzinfo=None)


def test_une_valeur_absente_n_efface_pas_une_valeur_connue(session):
    repo.enregistrer_entreprise(session, _e(activite="Conseil", distance_km=4.7), T1)
    repo.enregistrer_entreprise(session, _e(origine="lba", activite=None, distance_km=None), T2)
    lue = repo.lire_entreprise(session, 1)
    assert (lue.activite, lue.distance_km) == ("Conseil", 4.7)


def test_etat_de_contact_jamais_touche_par_une_source(session):
    repo.enregistrer_entreprise(session, _e(), T1)
    session.execute(
        update(entreprises).values(
            listee_le=datetime(2026, 11, 18, 8), contactee_le=datetime(2026, 11, 18, 9),
            ignoree_le=datetime(2026, 11, 18, 10),
        )
    )  # fmt: skip
    for origine in ("csv", "lba", "sirene"):
        repo.enregistrer_entreprise(session, _e(origine=origine, nom="Autre nom"), T2)
    ligne = _ligne(session)
    assert ligne["listee_le"] == datetime(2026, 11, 18, 8)
    assert ligne["contactee_le"] == datetime(2026, 11, 18, 9)
    assert ligne["ignoree_le"] == datetime(2026, 11, 18, 10)


def test_priorite_ecrasee_par_le_csv_seulement(session):
    repo.enregistrer_entreprise(session, _e(priorite=4), T1)
    repo.enregistrer_entreprise(session, _e(origine="lba", priorite=9), T2)
    repo.enregistrer_entreprise(session, _e(origine="sirene", priorite=8), T2)
    assert repo.lire_entreprise(session, 1).priorite == 4
    repo.enregistrer_entreprise(session, _e(origine="csv", priorite=2), T2)
    assert repo.lire_entreprise(session, 1).priorite == 2
    repo.enregistrer_entreprise(session, _e(origine="csv", priorite=None), T2)
    assert repo.lire_entreprise(session, 1).priorite == 2


def test_une_source_sans_priorite_n_en_donne_pas(session):
    repo.enregistrer_entreprise(session, _e(origine="lba"), T1)
    assert repo.lire_entreprise(session, 1).priorite is None


def test_origine_conservee_a_la_creation(session):
    repo.enregistrer_entreprise(session, _e(origine="csv"), T1)
    repo.enregistrer_entreprise(session, _e(origine="lba"), T2)
    assert repo.lire_entreprise(session, 1).origine == "csv"


def test_siret_invalide_refuse_par_le_modele():
    for mauvais in ("123", "1234567890001A", "123456789000111", ""):
        with pytest.raises(ValueError):
            _e(siret=mauvais)
