from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from denicheur.config import load_config
from denicheur.db import repo
from denicheur.db.base import make_engine, migrer
from denicheur.models import Offre, Piste, ScoreLLM, Statut
from denicheur.telegram.commands import repondre

CONFIG = load_config("config/recherches.yaml")
NOW = datetime(2026, 11, 16, 9, 0, tzinfo=UTC)  # 10:00 à Paris


@pytest.fixture
def session(tmp_path):
    url = f"sqlite:///{tmp_path / 'test.db'}"
    migrer(url)
    with Session(make_engine(url)) as s:
        yield s


def _offre(session, n, *, piste=Piste.ALTERNANCE, score=80, titre=None, notifiee=None):
    offre = Offre(
        source="lba", source_id=str(n), url=f"https://x/{n}", titre=titre or f"Dev {n}",
        entreprise="ACME", commune="Paris", lat=None, lon=None, piste=piste, duree_mois=None,
        debut=None, niveau_diplome=None, description="d", publiee_le=None, expire_le=None,
    )  # fmt: skip
    oid = repo.inserer_offre(session, offre, cle_dedup=f"k{n}", now=NOW)
    resultat = ScoreLLM(
        score=score, type=piste.value, points_forts=["a"], points_faibles=[], alerte=None,
        projet_a_citer="p", resume="r",
    )  # fmt: skip
    repo.inserer_score(
        session, oid, resultat, modele="m", prompt_tokens=1, output_tokens=1, duree_s=1, now=NOW
    )
    if notifiee:
        repo.marquer_notifiee(session, oid, notifiee)
    return oid


def _textes(reponses):
    return "\n".join(r.texte for r in reponses)


def _repondre(session, texte):
    return repondre(texte, session, CONFIG, NOW)


def test_aujourdhui_envoie_les_offres_du_jour_sans_suivi_avec_boutons(session):
    a = _offre(session, 1, notifiee=NOW - timedelta(hours=1), score=70)
    b = _offre(session, 2, notifiee=NOW - timedelta(hours=2), score=90)
    suivie = _offre(session, 3, notifiee=NOW)
    repo.marquer(session, suivie, Statut.IGNOREE, NOW)
    _offre(session, 4, notifiee=NOW - timedelta(days=1))  # d'hier
    reponses = _repondre(session, "/aujourdhui")
    offres = [r for r in reponses if r.clavier]
    assert [r.clavier["inline_keyboard"][0][0]["callback_data"] for r in offres] == [f"p:{b}", f"p:{a}"]
    assert "Dev 2" in offres[0].texte


def test_aujourdhui_vide(session):
    assert _textes(_repondre(session, "/aujourdhui")) == "Rien de nouveau aujourd'hui"


def test_stage_et_alternance_filtrent_par_piste_et_ecartent_les_ignorees(session):
    stage = _offre(session, 1, piste=Piste.STAGE, score=75)
    alt = _offre(session, 2, piste=Piste.ALTERNANCE, score=85)
    ecartee = _offre(session, 3, piste=Piste.STAGE, score=99)
    repo.marquer(session, ecartee, Statut.IGNOREE, NOW)
    cb = lambda rs: [r.clavier["inline_keyboard"][0][0]["callback_data"] for r in rs if r.clavier]  # noqa: E731
    assert cb(_repondre(session, "/stage")) == [f"p:{stage}"]
    assert cb(_repondre(session, "/alternance")) == [f"p:{alt}"]


def test_stage_limite_aux_cinq_meilleures(session):
    for n in range(8):
        _offre(session, n, piste=Piste.STAGE, score=60 + n)
    reponses = [r for r in _repondre(session, "/stage") if r.clavier]
    assert len(reponses) == 5
    assert "67/100" in reponses[0].texte


def test_candidatures_liste_le_suivi_en_cours_et_echappe_le_html(session):
    a = _offre(session, 1, titre="<b>Piège</b>")
    b = _offre(session, 2)
    c = _offre(session, 3)
    repo.marquer(session, a, Statut.CANDIDATURE_ENVOYEE, NOW)
    repo.marquer(session, b, Statut.INTERESSANTE, NOW)
    repo.marquer(session, c, Statut.IGNOREE, NOW)
    texte = _textes(_repondre(session, "/candidatures"))
    assert "&lt;b&gt;Piège&lt;/b&gt;" in texte and "<b>Piège" not in texte
    assert "Dev 2" in texte and "Dev 3" not in texte


def test_candidatures_vide(session):
    assert "Aucune candidature" in _textes(_repondre(session, "/candidatures"))


def test_relances(session):
    oid = _offre(session, 1)
    repo.marquer(session, oid, Statut.CANDIDATURE_ENVOYEE, NOW - timedelta(days=8))
    assert "Dev 1" in _textes(_repondre(session, "/relances"))
    repo.marquer_rappelee(session, oid, NOW)
    assert "Aucune relance" in _textes(_repondre(session, "/relances"))


def test_stats(session):
    oid = _offre(session, 1)
    repo.marquer(session, oid, Statut.CANDIDATURE_ENVOYEE, NOW)
    texte = _textes(_repondre(session, "/stats"))
    assert "candidature_envoyee" in texte and "1" in texte


def test_pause_puis_reprendre(session):
    assert "pause" in _textes(_repondre(session, "/pause")).lower()
    assert repo.get_param(session, "pause") == "1"
    assert "reprise" in _textes(_repondre(session, "/reprendre")).lower()
    assert repo.get_param(session, "pause") == "0"


def test_config_sans_secret(session):
    repo.set_param(session, "pause", "1")
    texte = _textes(_repondre(session, "/config"))
    assert str(CONFIG.score_min) in texte and "pause" in texte.lower()
    for interdit in ("token", "TOKEN", "password", "chat_id", "app_key", "KEY"):
        assert interdit not in texte


@pytest.mark.parametrize("texte", ["/bidule", "salut", "", "/"])
def test_commande_inconnue_liste_les_commandes(session, texte):
    reponse = _textes(_repondre(session, texte))
    assert "/aujourdhui" in reponse and "/reprendre" in reponse


def test_commande_avec_nom_du_bot_et_majuscules(session):
    _repondre(session, "/Pause@MonBot")
    assert repo.get_param(session, "pause") == "1"


def test_reponse_bornee_a_4096_caracteres(session):
    for n in range(60):
        oid = _offre(session, n, titre="T" * 190)
        repo.marquer(session, oid, Statut.INTERESSANTE, NOW)
    for r in _repondre(session, "/candidatures"):
        assert len(r.texte) <= 4096


def test_jour_paris_et_non_utc(session):
    # 23:30 UTC le 15 = 00:30 Paris le 16 : l'offre appartient au 16.
    _offre(session, 1, notifiee=datetime(2026, 11, 15, 23, 30, tzinfo=UTC))
    assert "Dev 1" in _textes(_repondre(session, "/aujourdhui"))
    assert date(2026, 11, 16) == NOW.astimezone(repo.PARIS).date()
