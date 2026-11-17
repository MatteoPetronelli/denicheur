from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from denicheur.db import repo
from denicheur.db.base import make_engine, migrer
from denicheur.db.tables import brouillons, candidatures
from denicheur.models import Offre, Piste, Statut

NOW = datetime(2026, 11, 17, 9, 0, tzinfo=UTC)


@pytest.fixture
def session(tmp_path):
    url = f"sqlite:///{tmp_path / 'test.db'}"
    migrer(url)
    with Session(make_engine(url)) as s:
        yield s


def _offre_id(session, n=1):
    offre = Offre(
        source="lba", source_id=str(n), url=f"https://x/{n}", titre=f"Dev {n}", entreprise="ACME",
        commune="Paris", lat=None, lon=None, piste=Piste.ALTERNANCE, duree_mois=None, debut=None,
        niveau_diplome=None, description="d", publiee_le=None, expire_le=None,
    )  # fmt: skip
    return repo.inserer_offre(session, offre, cle_dedup=f"k{n}", now=NOW)


def _lignes(session):
    return session.execute(select(brouillons)).mappings().all()


def test_brouillon_sur_offre_sans_suivi_cree_le_suivi_interessante(session):
    oid = _offre_id(session)
    bid = repo.enregistrer_brouillon(session, oid, "email", "Texte complet", NOW)
    assert repo.statut_de(session, oid) is Statut.INTERESSANTE
    (ligne,) = _lignes(session)
    cand = session.execute(select(candidatures.c.id).where(candidatures.c.offre_id == oid)).scalar_one()
    assert (ligne["id"], ligne["candidature_id"], ligne["type"]) == (bid, cand, "email")
    assert ligne["contenu"] == "Texte complet" and ligne["gmail_draft"] is False
    assert ligne["cree_le"] == datetime(2026, 11, 17, 9, 0)


def test_brouillon_sur_offre_deja_envoyee_laisse_le_statut(session):
    oid = _offre_id(session)
    repo.marquer(session, oid, Statut.CANDIDATURE_ENVOYEE, NOW)
    repo.enregistrer_brouillon(session, oid, "email", "t", NOW)
    assert repo.statut_de(session, oid) is Statut.CANDIDATURE_ENVOYEE


@pytest.mark.parametrize("statut", [Statut.IGNOREE, Statut.REFUS, Statut.ENTRETIEN])
def test_brouillon_refuse_sur_offre_ignoree_ou_a_issue_finale(session, statut):
    oid = _offre_id(session)
    repo.marquer(session, oid, Statut.CANDIDATURE_ENVOYEE, NOW)
    if statut is Statut.IGNOREE:
        repo.marquer(session, oid, Statut.IGNOREE, NOW)
    else:
        repo.marquer(session, oid, statut, NOW)
    with pytest.raises(repo.TransitionInvalide):
        repo.enregistrer_brouillon(session, oid, "email", "t", NOW)
    assert _lignes(session) == [] and repo.statut_de(session, oid) is statut


def test_brouillon_offre_inconnue(session):
    with pytest.raises(repo.OffreInconnue):
        repo.enregistrer_brouillon(session, 999, "email", "t", NOW)
    assert session.execute(select(candidatures)).all() == []


def test_premiere_relance_marque_relancee_et_date_la_relance(session):
    oid = _offre_id(session)
    repo.marquer(session, oid, Statut.CANDIDATURE_ENVOYEE, NOW)
    repo.enregistrer_brouillon(session, oid, "relance", "Relance", NOW)
    assert repo.statut_de(session, oid) is Statut.RELANCEE
    ligne = session.execute(select(candidatures)).mappings().one()
    assert ligne["relance_le"] == datetime(2026, 11, 17, 9, 0)
    assert [b["type"] for b in _lignes(session)] == ["relance"]


def test_seconde_relance_refusee_sans_nouveau_brouillon(session):
    oid = _offre_id(session)
    repo.marquer(session, oid, Statut.CANDIDATURE_ENVOYEE, NOW)
    repo.enregistrer_brouillon(session, oid, "relance", "Relance", NOW)
    with pytest.raises(repo.RelanceDejaFaite):
        repo.verifier_brouillon(session, oid, "relance")
    with pytest.raises(repo.RelanceDejaFaite):
        repo.enregistrer_brouillon(session, oid, "relance", "Autre", NOW)
    assert len(_lignes(session)) == 1


def test_relance_refusee_si_la_candidature_n_est_pas_envoyee(session):
    oid = _offre_id(session)
    repo.marquer(session, oid, Statut.INTERESSANTE, NOW)
    with pytest.raises(repo.TransitionInvalide):
        repo.enregistrer_brouillon(session, oid, "relance", "t", NOW)
    assert repo.statut_de(session, oid) is Statut.INTERESSANTE and _lignes(session) == []


def test_relance_refusee_sur_offre_sans_suivi(session):
    oid = _offre_id(session)
    with pytest.raises(repo.TransitionInvalide):
        repo.verifier_brouillon(session, oid, "relance")
    assert session.execute(select(candidatures)).all() == []


def test_relance_d_une_offre_n_empeche_pas_celle_d_une_autre(session):
    a, b = _offre_id(session, 1), _offre_id(session, 2)
    for oid in (a, b):
        repo.marquer(session, oid, Statut.CANDIDATURE_ENVOYEE, NOW)
    repo.enregistrer_brouillon(session, a, "relance", "r", NOW)
    repo.enregistrer_brouillon(session, b, "relance", "r", NOW)
    assert len(_lignes(session)) == 2


def test_lire_puis_marquer_depose(session):
    oid = _offre_id(session)
    bid = repo.enregistrer_brouillon(session, oid, "email", "Corps", NOW)
    lu = repo.lire_brouillon(session, bid)
    assert lu is not None
    assert (lu.id, lu.offre_id, lu.type, lu.contenu, lu.depose) == (bid, oid, "email", "Corps", False)
    repo.marquer_depose(session, bid)
    lu = repo.lire_brouillon(session, bid)
    assert lu is not None and lu.depose is True


def test_lire_brouillon_inconnu(session):
    assert repo.lire_brouillon(session, 999) is None
