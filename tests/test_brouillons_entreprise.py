from datetime import UTC, date, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from denicheur.db import repo
from denicheur.db.base import make_engine, migrer
from denicheur.db.tables import brouillons, candidatures
from denicheur.models import Entreprise, Offre, Piste, Statut

NOW = datetime(2026, 11, 18, 9, tzinfo=UTC)
MAX = 15


@pytest.fixture
def session(tmp_path):
    url = f"sqlite:///{tmp_path / 'test.db'}"
    migrer(url)
    with Session(make_engine(url)) as s:
        yield s


def _ent(session, n=1):
    e = Entreprise(siret=f"{n:09d}00011", nom=f"E{n}", origine="csv")
    return repo.enregistrer_entreprise(session, e, NOW)[0]


def _brouillon(session, eid, type_="spontanee", now=NOW, maximum=MAX):
    return repo.enregistrer_brouillon_entreprise(session, eid, type_, f"texte {type_}", now, maximum)


def _suivis(session):
    return session.execute(select(candidatures)).mappings().all()


def _nb_brouillons(session):
    return len(session.execute(select(brouillons)).all())


def test_brouillon_sur_une_entreprise_sans_suivi_cree_le_suivi_interessante(session):
    eid = _ent(session)
    bid = _brouillon(session, eid)
    (suivi,) = _suivis(session)
    assert (suivi["offre_id"], suivi["entreprise_id"], suivi["statut"]) == (None, eid, "interessante")
    assert suivi["envoyee_le"] is None
    ligne = session.execute(select(brouillons).where(brouillons.c.id == bid)).mappings().one()
    assert (ligne["candidature_id"], ligne["type"], ligne["contenu"]) == (
        suivi["id"],
        "spontanee",
        "texte spontanee",
    )
    assert ligne["gmail_draft"] == 0 and ligne["cree_le"] == datetime(2026, 11, 18, 9)
    assert repo.statut_de_entreprise(session, eid) is Statut.INTERESSANTE


def test_message_puis_lettre_sur_la_meme_entreprise_un_seul_suivi(session):
    eid = _ent(session)
    _brouillon(session, eid, "spontanee")
    _brouillon(session, eid, "lettre")
    assert len(_suivis(session)) == 1 and _nb_brouillons(session) == 2


@pytest.mark.parametrize("statut", [Statut.IGNOREE, Statut.CANDIDATURE_ENVOYEE])
def test_entreprise_ecartee_ou_contactee_refusee_sans_rien_ecrire(session, statut):
    eid = _ent(session)
    repo.marquer_entreprise(session, eid, statut, NOW)
    with pytest.raises(repo.TransitionInvalide):
        _brouillon(session, eid)
    assert _nb_brouillons(session) == 0


@pytest.mark.parametrize("issue", [Statut.REFUS, Statut.ENTRETIEN, Statut.SANS_REPONSE, Statut.OFFRE])
def test_entreprise_a_issue_finale_refusee(session, issue):
    eid = _ent(session)
    repo.marquer_entreprise(session, eid, Statut.CANDIDATURE_ENVOYEE, NOW)
    repo.marquer_entreprise(session, eid, issue, NOW)
    with pytest.raises(repo.TransitionInvalide):
        _brouillon(session, eid)


def test_entreprise_relancee_refusee(session):
    eid = _ent(session)
    repo.marquer_entreprise(session, eid, Statut.CANDIDATURE_ENVOYEE, NOW)
    repo.marquer_entreprise(session, eid, Statut.RELANCEE, NOW)
    with pytest.raises(repo.TransitionInvalide):
        _brouillon(session, eid)


def test_entreprise_inconnue(session):
    with pytest.raises(repo.EntrepriseInconnue):
        _brouillon(session, 99)
    assert _suivis(session) == [] and _nb_brouillons(session) == 0


@pytest.mark.parametrize("type_", ["relance", "email", "inconnu", ""])
def test_jamais_de_relance_ni_de_type_d_offre_pour_une_entreprise(session, type_):
    eid = _ent(session)
    with pytest.raises(ValueError):
        _brouillon(session, eid, type_)
    assert _suivis(session) == [] and _nb_brouillons(session) == 0


def test_verifier_n_ecrit_rien(session):
    eid = _ent(session)
    repo.verifier_brouillon_entreprise(session, eid, "lettre", NOW, MAX)
    assert _suivis(session) == [] and _nb_brouillons(session) == 0


# --- plafond du jour ---
def test_le_seizieme_brouillon_du_jour_est_refuse_et_rien_n_est_ecrit(session):
    for n in range(1, 16):
        _brouillon(session, _ent(session, n))
    dernier = _ent(session, 16)
    with pytest.raises(repo.PlafondAtteint):
        _brouillon(session, dernier)
    with pytest.raises(repo.PlafondAtteint):
        repo.verifier_brouillon_entreprise(session, dernier, "spontanee", NOW, MAX)
    assert _nb_brouillons(session) == 15 and repo.statut_de_entreprise(session, dernier) is None


def test_le_plafond_compte_chaque_brouillon_pas_chaque_entreprise(session):
    eid = _ent(session)
    for _ in range(15):
        _brouillon(session, eid)
    with pytest.raises(repo.PlafondAtteint):
        _brouillon(session, eid, "lettre")


def test_lendemain_paris_le_compteur_repart(session):
    for n in range(1, 16):
        _brouillon(session, _ent(session, n), now=datetime(2026, 11, 18, 22, 30, tzinfo=UTC))  # 23:30 Paris
    suivant = _ent(session, 16)
    _brouillon(session, suivant, now=datetime(2026, 11, 18, 23, 30, tzinfo=UTC))  # 00:30 Paris, le 19
    assert _nb_brouillons(session) == 16
    assert repo.nb_brouillons_entreprise_le(session, date(2026, 11, 18)) == 15
    assert repo.nb_brouillons_entreprise_le(session, date(2026, 11, 19)) == 1


def test_les_brouillons_d_offres_ne_comptent_pas(session):
    for n in range(1, 16):
        o = Offre(
            source="t", source_id=str(n), url=f"https://x/{n}", titre="Dev", entreprise="ACME", commune=None,
            lat=None, lon=None, piste=Piste.ALTERNANCE, duree_mois=None, debut=None, niveau_diplome=None,
            description="d", publiee_le=None, expire_le=None,
        )  # fmt: skip
        oid = repo.inserer_offre(session, o, cle_dedup=f"k{n}", now=NOW)
        repo.enregistrer_brouillon(session, oid, "email", "texte", NOW)
    assert repo.nb_brouillons_entreprise_le(session, date(2026, 11, 18)) == 0
    _brouillon(session, _ent(session))


def test_plafond_configurable(session):
    _brouillon(session, _ent(session, 1), maximum=2)
    _brouillon(session, _ent(session, 2), maximum=2)
    with pytest.raises(repo.PlafondAtteint):
        _brouillon(session, _ent(session, 3), maximum=2)


def test_plafond_a_zero_refuse_tout(session):
    with pytest.raises(repo.PlafondAtteint):
        _brouillon(session, _ent(session), maximum=0)


# --- relecture et dépôt ---
def test_lire_un_brouillon_d_entreprise(session):
    eid = _ent(session)
    bid = _brouillon(session, eid, "lettre")
    lu = repo.lire_brouillon(session, bid)
    assert (lu.offre_id, lu.entreprise_id, lu.type, lu.contenu, lu.depose) == (
        None, eid, "lettre", "texte lettre", False,
    )  # fmt: skip


def test_lire_un_brouillon_d_offre_n_a_pas_d_entreprise(session):
    o = Offre(
        source="t", source_id="1", url="https://x/1", titre="Dev", entreprise="ACME", commune=None, lat=None,
        lon=None, piste=Piste.ALTERNANCE, duree_mois=None, debut=None, niveau_diplome=None,
        description="d", publiee_le=None, expire_le=None,
    )  # fmt: skip
    oid = repo.inserer_offre(session, o, cle_dedup="k", now=NOW)
    lu = repo.lire_brouillon(session, repo.enregistrer_brouillon(session, oid, "email", "t", NOW))
    assert (lu.offre_id, lu.entreprise_id) == (oid, None)


def test_depot_gmail_d_un_brouillon_d_entreprise(session):
    bid = _brouillon(session, _ent(session))
    repo.marquer_depose(session, bid)
    assert repo.lire_brouillon(session, bid).depose is True
