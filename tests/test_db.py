from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from denicheur.db import repo
from denicheur.db.base import make_engine, migrer
from denicheur.models import Offre, Piste, ScoreLLM

PARIS = ZoneInfo("Europe/Paris")


@pytest.fixture
def url(tmp_path):
    return f"sqlite:///{tmp_path / 'test.db'}"


@pytest.fixture
def session(url):
    migrer(url)
    engine = make_engine(url)
    with Session(engine) as s:
        yield s


def _offre(source_id="1", url="https://x/1", **kw):
    base = {
        "source": "lba", "source_id": source_id, "url": url, "titre": "Dev", "entreprise": "ACME",
        "commune": "Paris", "lat": 48.85, "lon": 2.39, "piste": Piste.ALTERNANCE, "duree_mois": 12,
        "debut": date(2027, 1, 4), "debut_des_que_possible": True, "niveau_diplome": "7",
        "description": "desc", "publiee_le": datetime(2026, 11, 1, tzinfo=UTC), "expire_le": None,
    }  # fmt: skip
    return Offre(**{**base, **kw})


def _score(n=80):
    return ScoreLLM(
        score=n, type="alternance", points_forts=["a", "b"], points_faibles=["c"],
        alerte="⚠️", projet_a_citer="p", resume="r",
    )  # fmt: skip


def test_migration_cree_six_tables(url):
    migrer(url)
    noms = set(inspect(make_engine(url)).get_table_names())
    assert {"offres", "scores", "candidatures", "brouillons", "executions", "parametres"} <= noms


def test_migration_deux_fois(url):
    migrer(url)
    migrer(url)


def test_wal_active(url):
    with make_engine(url).connect() as c:
        assert c.execute(text("PRAGMA journal_mode")).scalar() == "wal"


def test_offre_et_score_aller_retour(session):
    o = _offre()
    oid = repo.inserer_offre(session, o, cle_dedup="k1", now=datetime(2026, 11, 16, 8, tzinfo=UTC))
    repo.inserer_score(
        session, oid, _score(), modele="m", prompt_tokens=10, output_tokens=5, duree_s=1.5,
        now=datetime(2026, 11, 16, 8, tzinfo=UTC),
    )  # fmt: skip
    session.commit()
    assert repo.lire_offre(session, oid) == o
    s = repo.lire_score(session, oid)
    assert s == _score()
    assert s.points_forts == ["a", "b"]


def test_double_insertion_idempotente(session):
    now = datetime(2026, 11, 16, 8, tzinfo=UTC)
    a = repo.inserer_offre(session, _offre(), cle_dedup="k", now=now)
    b = repo.inserer_offre(session, _offre(), cle_dedup="k", now=now)
    assert a == b
    assert session.execute(text("select count(*) from offres")).scalar() == 1


def test_url_dupliquee_idempotente(session):
    now = datetime(2026, 11, 16, 8, tzinfo=UTC)
    a = repo.inserer_offre(session, _offre("1", "https://x/1"), cle_dedup="k", now=now)
    b = repo.inserer_offre(session, _offre("2", "https://x/1"), cle_dedup="k", now=now)
    assert a == b


def test_urls_et_cles_connues(session):
    now = datetime(2026, 11, 16, 8, tzinfo=UTC)
    repo.inserer_offre(session, _offre("1", "https://x/1"), cle_dedup="k1", now=now)
    repo.inserer_offre(session, _offre("2", "https://x/2"), cle_dedup="k2", now=now)
    assert repo.urls_connues(session) == {"https://x/1", "https://x/2"}
    assert repo.cles_connues(session) == {"k1", "k2"}


def test_appels_llm_jour_paris(session):
    for i, quand in enumerate(
        [
            datetime(2026, 11, 15, 23, 30, tzinfo=PARIS),  # hier Paris
            datetime(2026, 11, 16, 0, 10, tzinfo=PARIS),  # aujourd'hui Paris (23:10 UTC la veille)
        ]
    ):
        oid = repo.inserer_offre(session, _offre(str(i), f"https://x/{i}"), cle_dedup=str(i), now=quand)
        repo.inserer_score(session, oid, _score(), modele="m", prompt_tokens=1, output_tokens=1,
                           duree_s=0.1, now=quand)  # fmt: skip
    session.commit()
    assert repo.appels_llm_aujourdhui(session, datetime(2026, 11, 16, 12, tzinfo=PARIS)) == 1


def test_parametres_ecrasement(session):
    assert repo.get_param(session, "pause") is None
    repo.set_param(session, "pause", "0")
    repo.set_param(session, "pause", "1")
    session.commit()
    assert repo.get_param(session, "pause") == "1"


def test_score_unique_par_offre(session):
    now = datetime(2026, 11, 16, 8, tzinfo=UTC)
    oid = repo.inserer_offre(session, _offre(), cle_dedup="k", now=now)
    repo.inserer_score(
        session, oid, _score(), modele="m", prompt_tokens=1, output_tokens=1, duree_s=1, now=now
    )
    with pytest.raises(Exception):  # noqa: B017 — IntegrityError sur offre_id unique
        repo.inserer_score(session, oid, _score(), modele="m", prompt_tokens=1, output_tokens=1,
                           duree_s=1, now=now)  # fmt: skip
        session.flush()
