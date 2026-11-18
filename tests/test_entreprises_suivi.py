from datetime import UTC, date, datetime

import pytest
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from denicheur.db import repo
from denicheur.db.base import make_engine, migrer
from denicheur.db.tables import candidatures, entreprises, offres
from denicheur.models import Entreprise, Offre, Piste, Statut

NOW = datetime(2026, 11, 18, 9, tzinfo=UTC)
LATER = datetime(2026, 11, 19, 9, tzinfo=UTC)


@pytest.fixture
def session(tmp_path):
    url = f"sqlite:///{tmp_path / 'test.db'}"
    migrer(url)
    with Session(make_engine(url)) as s:
        yield s


def _siret(n):
    return f"{n:09d}00011"


def _ent(session, n, priorite=None, distance=5.0, origine="csv", **kw):
    e = Entreprise(
        siret=_siret(n), nom=f"E{n}", priorite=priorite, distance_km=distance, origine=origine, **kw
    )
    return repo.enregistrer_entreprise(session, e, NOW)[0]


def _ids(liste):
    return [i for i, _ in liste]


def _ligne(session, eid):
    return session.execute(select(entreprises).where(entreprises.c.id == eid)).mappings().one()


# --- sélection de la liste du jour ---
def test_ordre_priorite_croissante_puis_sans_priorite_puis_distance_puis_id(session):
    a = _ent(session, 1, priorite=2, distance=1.0)
    b = _ent(session, 2, priorite=1, distance=9.0)
    c = _ent(session, 3, priorite=None, distance=2.0)
    d = _ent(session, 4, priorite=None, distance=1.0)
    e = _ent(session, 5, priorite=None, distance=None)
    f = _ent(session, 6, priorite=None, distance=1.0)
    assert _ids(repo.entreprises_du_jour(session, 10)) == [b, a, d, f, c, e]


def test_limite_de_la_liste(session):
    for n in range(1, 41):
        _ent(session, n, priorite=n)
    liste = repo.entreprises_du_jour(session, 10)
    assert _ids(liste) == list(range(1, 11))
    assert liste[0][1].nom == "E1"


def test_limite_zero_ou_negative_ne_renvoie_rien(session):
    _ent(session, 1)
    assert repo.entreprises_du_jour(session, 0) == []
    assert repo.entreprises_du_jour(session, -3) == []


@pytest.mark.parametrize("colonne", ["listee_le", "contactee_le", "ignoree_le"])
def test_entreprise_deja_listee_contactee_ou_ecartee_exclue(session, colonne):
    a, b = _ent(session, 1, priorite=1), _ent(session, 2, priorite=2)
    session.execute(update(entreprises).where(entreprises.c.id == a).values({colonne: datetime(2026, 11, 1)}))
    assert _ids(repo.entreprises_du_jour(session, 10)) == [b]


def test_marquer_listee_retire_l_entreprise_des_listes_suivantes(session):
    a, b = _ent(session, 1, priorite=1), _ent(session, 2, priorite=2)
    repo.marquer_listee(session, a, NOW)
    assert _ligne(session, a)["listee_le"] == datetime(2026, 11, 18, 9)
    assert _ids(repo.entreprises_du_jour(session, 10)) == [b]
    assert _ids(repo.entreprises_du_jour(session, 10)) == [b]  # idempotent


def test_une_entreprise_avec_une_offre_ouverte_reste_eligible(session):
    a = _ent(session, 1)
    _offre(session, 1, siret=_siret(1))
    assert _ids(repo.entreprises_du_jour(session, 10)) == [a]


def test_nombre_d_entreprises_listees_dans_la_journee_paris(session):
    ids = [_ent(session, n) for n in range(1, 5)]
    repo.marquer_listee(session, ids[0], datetime(2026, 11, 18, 8, tzinfo=UTC))
    repo.marquer_listee(session, ids[1], datetime(2026, 11, 18, 22, 30, tzinfo=UTC))  # 23:30 Paris, même jour
    repo.marquer_listee(session, ids[2], datetime(2026, 11, 18, 23, 30, tzinfo=UTC))  # 00:30 Paris, lendemain
    repo.marquer_listee(session, ids[3], datetime(2026, 11, 17, 22, 59, tzinfo=UTC))  # 23:59 Paris, veille
    assert repo.nb_listees_le(session, date(2026, 11, 18)) == 2
    assert repo.nb_listees_le(session, date(2026, 11, 19)) == 1
    assert repo.nb_listees_le(session, date(2026, 11, 17)) == 1


# --- offres ouvertes du même SIRET ---
def _offre(session, n, siret=None, **kw):
    base = {
        "source": "lba", "source_id": str(n), "url": f"https://x/{n}", "titre": f"Dev {n}",
        "entreprise": "ACME", "siret": siret, "commune": "Paris", "lat": None, "lon": None,
        "piste": Piste.ALTERNANCE, "duree_mois": None, "debut": None, "niveau_diplome": None,
        "description": "d", "publiee_le": None, "expire_le": None,
    }  # fmt: skip
    return repo.inserer_offre(session, Offre(**{**base, **kw}), cle_dedup=f"k{n}", now=NOW)


def test_offres_ouvertes_rapprochees_par_siret_exact_seulement(session):
    _offre(session, 1, siret=_siret(1), titre="Alternance dev")
    _offre(session, 2, siret=_siret(2), titre="Autre entreprise")
    _offre(session, 3, siret=None, titre="Même nom, sans SIRET", entreprise="E1")
    rejetee = _offre(session, 4, siret=_siret(1), titre="Rejetée")
    session.execute(update(offres).where(offres.c.id == rejetee).values(motif_rejet="mots_cles_absents"))
    assert repo.titres_offres_du_siret(session, _siret(1)) == ["Alternance dev"]
    assert repo.titres_offres_du_siret(session, _siret(9)) == []


def test_offres_du_siret_les_plus_recentes_d_abord_et_bornees(session):
    for n in range(1, 8):
        _offre(session, n, siret=_siret(1), titre=f"T{n}")
    assert repo.titres_offres_du_siret(session, _siret(1), limite=3) == ["T7", "T6", "T5"]


# --- suivi d'une entreprise ---
def test_envoyee_cree_le_suivi_sans_offre_et_pose_la_date_de_contact(session):
    eid = _ent(session, 1)
    repo.marquer_entreprise(session, eid, Statut.CANDIDATURE_ENVOYEE, NOW)
    (ligne,) = session.execute(select(candidatures)).mappings().all()
    assert (ligne["offre_id"], ligne["entreprise_id"], ligne["statut"]) == (None, eid, "candidature_envoyee")
    assert ligne["envoyee_le"] == datetime(2026, 11, 18, 9)
    assert _ligne(session, eid)["contactee_le"] == datetime(2026, 11, 18, 9)
    assert _ligne(session, eid)["ignoree_le"] is None
    assert repo.statut_de_entreprise(session, eid) is Statut.CANDIDATURE_ENVOYEE


def test_ecarter_pose_la_date_et_cree_un_suivi_ignoree(session):
    eid = _ent(session, 1)
    repo.marquer_entreprise(session, eid, Statut.IGNOREE, NOW)
    assert repo.statut_de_entreprise(session, eid) is Statut.IGNOREE
    assert _ligne(session, eid)["ignoree_le"] == datetime(2026, 11, 18, 9)
    assert _ligne(session, eid)["contactee_le"] is None


def test_deuxieme_marquage_identique_ne_change_rien(session):
    eid = _ent(session, 1)
    repo.marquer_entreprise(session, eid, Statut.CANDIDATURE_ENVOYEE, NOW)
    repo.marquer_entreprise(session, eid, Statut.CANDIDATURE_ENVOYEE, LATER)
    assert _ligne(session, eid)["contactee_le"] == datetime(2026, 11, 18, 9)
    assert len(session.execute(select(candidatures)).all()) == 1


def test_entreprise_inconnue_refusee_sans_ecriture(session):
    with pytest.raises(repo.EntrepriseInconnue):
        repo.marquer_entreprise(session, 99, Statut.CANDIDATURE_ENVOYEE, NOW)
    assert session.execute(select(candidatures)).all() == []
    assert repo.statut_de_entreprise(session, 99) is None


def test_transition_refusee_laisse_les_dates_inchangees(session):
    eid = _ent(session, 1)
    repo.marquer_entreprise(session, eid, Statut.IGNOREE, NOW)
    with pytest.raises(repo.TransitionInvalide):
        repo.marquer_entreprise(session, eid, Statut.CANDIDATURE_ENVOYEE, LATER)
    assert _ligne(session, eid)["contactee_le"] is None
    assert repo.statut_de_entreprise(session, eid) is Statut.IGNOREE


def test_envoyee_puis_ecartee_garde_les_deux_dates(session):
    eid = _ent(session, 1)
    repo.marquer_entreprise(session, eid, Statut.CANDIDATURE_ENVOYEE, NOW)
    repo.marquer_entreprise(session, eid, Statut.IGNOREE, LATER)
    ligne = _ligne(session, eid)
    assert (ligne["contactee_le"], ligne["ignoree_le"]) == (
        datetime(2026, 11, 18, 9),
        datetime(2026, 11, 19, 9),
    )


def test_interessante_puis_envoyee_met_a_jour_la_meme_ligne(session):
    eid = _ent(session, 1)
    repo.marquer_entreprise(session, eid, Statut.INTERESSANTE, NOW)
    assert _ligne(session, eid)["contactee_le"] is None
    repo.marquer_entreprise(session, eid, Statut.CANDIDATURE_ENVOYEE, LATER)
    assert len(session.execute(select(candidatures)).all()) == 1
    assert _ligne(session, eid)["contactee_le"] == datetime(2026, 11, 19, 9)


def test_offre_et_entreprise_de_meme_identifiant_ne_se_melangent_pas(session):
    eid = _ent(session, 1)
    oid = _offre(session, 1)
    assert eid == oid == 1
    repo.marquer(session, oid, Statut.IGNOREE, NOW)
    assert repo.statut_de_entreprise(session, eid) is None
    repo.marquer_entreprise(session, eid, Statut.CANDIDATURE_ENVOYEE, NOW)
    assert repo.statut_de(session, oid) is Statut.IGNOREE
    assert len(session.execute(select(candidatures)).all()) == 2


# --- les suivis d'entreprise (offre_id nul) ne perturbent pas les requêtes sur les offres ---
def _score(n=80):
    from denicheur.models import ScoreLLM

    return ScoreLLM(
        score=n, type="alternance", points_forts=["a"], points_faibles=[], alerte=None,
        projet_a_citer="p", resume="r",
    )  # fmt: skip


def _offre_notee(session, n, notifiee=True):
    oid = _offre(session, n)
    repo.inserer_score(
        session, oid, _score(70 + n), modele="m", prompt_tokens=1, output_tokens=1, duree_s=1, now=NOW
    )
    if notifiee:
        repo.marquer_notifiee(session, oid, NOW)
    return oid


def _suivis_d_entreprises(session):
    for n, statut in enumerate((Statut.IGNOREE, Statut.CANDIDATURE_ENVOYEE, Statut.INTERESSANTE), start=1):
        eid = _ent(session, n)
        repo.marquer_entreprise(session, eid, statut, datetime(2026, 11, 1, 9, tzinfo=UTC))


def test_requetes_sur_les_offres_ignorent_les_suivis_d_entreprises(session):
    oid = _offre_notee(session, 1)
    autre = _offre_notee(session, 2)
    repo.marquer(session, autre, Statut.IGNOREE, NOW)
    _suivis_d_entreprises(session)
    jour = date(2026, 11, 18)
    assert [i for i, _, _ in repo.offres_du_jour(session, jour)] == [oid]
    assert [i for i, _, _ in repo.meilleures_offres(session, Piste.ALTERNANCE, 10)] == [oid]
    assert repo.stats(session).nouvelles == 1
    assert [i for i, _, _ in repo.suivi_en_cours(session, 10)] == []
    assert repo.candidatures_a_relancer(session, date(2026, 12, 1)) == []


def test_les_statistiques_comptent_aussi_les_entreprises_par_statut(session):
    _suivis_d_entreprises(session)
    assert repo.stats(session).par_statut == {"ignoree": 1, "candidature_envoyee": 1, "interessante": 1}
