from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from denicheur.db import repo
from denicheur.db.base import make_engine, migrer
from denicheur.db.tables import candidatures
from denicheur.models import Offre, Piste, Statut

NOW = datetime(2026, 11, 16, 9, 0, tzinfo=UTC)


@pytest.fixture
def session(tmp_path):
    url = f"sqlite:///{tmp_path / 'test.db'}"
    migrer(url)
    with Session(make_engine(url)) as s:
        yield s


def _offre_id(session, n=1, **kw):
    base = {
        "source": "lba", "source_id": str(n), "url": f"https://x/{n}", "titre": f"Dev {n}",
        "entreprise": "ACME", "commune": "Paris", "lat": None, "lon": None, "piste": Piste.ALTERNANCE,
        "duree_mois": None, "debut": None, "niveau_diplome": None, "description": "d",
        "publiee_le": None, "expire_le": None,
    }  # fmt: skip
    return repo.inserer_offre(session, Offre(**{**base, **kw}), cle_dedup=f"k{n}", now=NOW)


def _lignes(session):
    return session.execute(select(candidatures)).mappings().all()


def test_premier_marquage_cree_la_ligne_avec_la_date_d_envoi(session):
    oid = _offre_id(session)
    repo.marquer(session, oid, Statut.CANDIDATURE_ENVOYEE, NOW)
    (ligne,) = _lignes(session)
    assert (ligne["offre_id"], ligne["statut"]) == (oid, "candidature_envoyee")
    assert ligne["envoyee_le"] == datetime(2026, 11, 16, 9, 0)
    assert ligne["cree_le"] == ligne["maj_le"] == datetime(2026, 11, 16, 9, 0)


def test_une_seule_ligne_par_offre(session):
    oid = _offre_id(session)
    repo.marquer(session, oid, Statut.INTERESSANTE, NOW)
    repo.marquer(session, oid, Statut.CANDIDATURE_ENVOYEE, NOW + timedelta(hours=1))
    (ligne,) = _lignes(session)
    assert ligne["statut"] == "candidature_envoyee"
    assert ligne["cree_le"] == datetime(2026, 11, 16, 9, 0)
    assert ligne["maj_le"] == datetime(2026, 11, 16, 10, 0)


def test_interessante_ne_pose_pas_de_date_d_envoi(session):
    oid = _offre_id(session)
    repo.marquer(session, oid, Statut.INTERESSANTE, NOW)
    assert _lignes(session)[0]["envoyee_le"] is None


@pytest.mark.parametrize(
    ("depart", "arrivee"),
    [
        (Statut.IGNOREE, Statut.CANDIDATURE_ENVOYEE),
        (Statut.INTERESSANTE, Statut.REFUS),
        (Statut.CANDIDATURE_ENVOYEE, Statut.INTERESSANTE),
        (Statut.REFUS, Statut.ENTRETIEN),
        (Statut.INTERESSANTE, Statut.RELANCEE),
    ],
)
def test_transition_refusee_laisse_la_base_inchangee(session, depart, arrivee):
    oid = _offre_id(session)
    if depart is Statut.IGNOREE or depart is Statut.INTERESSANTE:
        repo.marquer(session, oid, depart, NOW)
    else:
        repo.marquer(session, oid, Statut.CANDIDATURE_ENVOYEE, NOW)
        repo.marquer(session, oid, depart, NOW)
    avant = [dict(r) for r in _lignes(session)]
    with pytest.raises(repo.TransitionInvalide):
        repo.marquer(session, oid, arrivee, NOW + timedelta(days=1))
    assert [dict(r) for r in _lignes(session)] == avant


def test_ignorer_depuis_n_importe_quel_statut(session):
    oid = _offre_id(session)
    repo.marquer(session, oid, Statut.CANDIDATURE_ENVOYEE, NOW)
    repo.marquer(session, oid, Statut.ENTRETIEN, NOW)
    repo.marquer(session, oid, Statut.IGNOREE, NOW)
    assert _lignes(session)[0]["statut"] == "ignoree"


def test_chaine_complete_de_suivi(session):
    oid = _offre_id(session)
    for statut in (Statut.CANDIDATURE_ENVOYEE, Statut.RELANCEE, Statut.ENTRETIEN):
        repo.marquer(session, oid, statut, NOW)
    assert _lignes(session)[0]["statut"] == "entretien"


def test_meme_statut_conserve_la_date_d_origine(session):
    oid = _offre_id(session)
    repo.marquer(session, oid, Statut.CANDIDATURE_ENVOYEE, NOW)
    repo.marquer(session, oid, Statut.CANDIDATURE_ENVOYEE, NOW + timedelta(days=3))
    (ligne,) = _lignes(session)
    assert ligne["envoyee_le"] == datetime(2026, 11, 16, 9, 0)
    assert ligne["maj_le"] == datetime(2026, 11, 16, 9, 0)


def test_offre_inconnue_refusee_sans_ecriture(session):
    with pytest.raises(repo.OffreInconnue):
        repo.marquer(session, 999, Statut.IGNOREE, NOW)
    assert _lignes(session) == []


def _envoyee(session, n, jours):
    oid = _offre_id(session, n)
    repo.marquer(session, oid, Statut.CANDIDATURE_ENVOYEE, NOW - timedelta(days=jours))
    return oid


def test_a_relancer_sept_jours_pas_six(session):
    sept, _six = _envoyee(session, 1, 7), _envoyee(session, 2, 6)
    due = repo.candidatures_a_relancer(session, date(2026, 11, 16))
    assert [oid for oid, _ in due] == [sept]
    assert due[0][1].titre == "Dev 1"


def test_a_relancer_exclut_deja_rappelee_et_autres_statuts(session):
    rappelee = _envoyee(session, 1, 10)
    session.execute(candidatures.update().where(candidatures.c.offre_id == rappelee).values(rappel_le=NOW))
    autre = _envoyee(session, 2, 10)
    repo.marquer(session, autre, Statut.REFUS, NOW)
    assert repo.candidatures_a_relancer(session, date(2026, 11, 16)) == []


def test_marquer_rappelee_retire_la_candidature_des_relances(session):
    oid = _envoyee(session, 1, 8)
    repo.marquer_rappelee(session, oid, NOW)
    assert repo.candidatures_a_relancer(session, date(2026, 11, 16)) == []


def test_stats(session):
    ids = [_offre_id(session, n) for n in range(1, 8)]
    repo.marquer(session, ids[0], Statut.CANDIDATURE_ENVOYEE, NOW)
    repo.marquer(session, ids[1], Statut.CANDIDATURE_ENVOYEE, NOW)
    repo.marquer(session, ids[2], Statut.IGNOREE, NOW)
    for i in (3, 4, 5):
        repo.marquer_notifiee(session, ids[i], NOW)
    repo.marquer_notifiee(session, ids[0], NOW)  # notifiée mais déjà suivie : pas « nouvelle »
    session.execute(repo.offres.update().where(repo.offres.c.id == ids[6]).values(motif_rejet="loin"))
    s = repo.stats(session)
    assert s.par_statut == {"candidature_envoyee": 2, "ignoree": 1}
    assert (s.nouvelles, s.rejetees) == (3, 1)
    assert session.execute(select(func.count()).select_from(candidatures)).scalar_one() == 3
