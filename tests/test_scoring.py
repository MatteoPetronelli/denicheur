import json
import re
from datetime import UTC, date, datetime
from pathlib import Path

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from denicheur.config import load_config
from denicheur.db import repo
from denicheur.db.base import make_engine, migrer
from denicheur.models import Offre, Piste, ScoreLLM
from denicheur.pipeline.dedupe import cle_dedup
from denicheur.scoring.compare import ScorerFactice, comparer
from denicheur.scoring.llm import OllamaIndisponible, OllamaScorer, ScoreInvalide, Usage
from denicheur.scoring.prompts import system_scoring, user_message
from denicheur.scoring.service import scorer_offres
from denicheur.sources.la_bonne_alternance import collecter

RACINE = Path(__file__).parent.parent
FIXTURE = json.loads((RACINE / "tests" / "fixtures" / "lba_search.json").read_text(encoding="utf-8"))
cfg = load_config(RACINE / "config" / "recherches.yaml")
NOW = datetime(2026, 11, 16, 9, tzinfo=UTC)
TEL = re.compile(r"\b0\d([\s.-]?\d{2}){4}\b")
JOUR = date(2026, 11, 16)


def _offres():
    client = httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=FIXTURE)),
        headers={"Authorization": "Bearer k"},
    )
    return collecter(cfg, client, NOW)


def _offre(**kw):
    base = {
        "source": "t", "source_id": "1", "url": "u1", "titre": "Développeur Python", "entreprise": "ACME",
        "commune": "Paris", "lat": 48.88, "lon": 2.0775, "piste": Piste.ALTERNANCE, "duree_mois": 12,
        "debut": None, "niveau_diplome": "7", "description": "desc", "publiee_le": NOW, "expire_le": None,
        "distance_km": 4.2,
    }  # fmt: skip
    return Offre(**{**base, **kw})


def _score(n=80):
    return ScoreLLM(
        score=n, type="alternance", points_forts=["a"], points_faibles=["b"], alerte=None,
        projet_a_citer="RiftMind", resume="r",
    )  # fmt: skip


# --- prompts ---
def test_prompt_systeme_stable_et_sans_date():
    assert system_scoring() == system_scoring()
    assert not re.search(r"\d{4}-\d{2}-\d{2}", system_scoring())  # pas de date du jour
    assert "RiftMind" in system_scoring()  # profil inclus
    assert "présentiel" in system_scoring()  # l'école exige du présentiel


def test_message_utilisateur_contient_la_date_du_jour():
    assert "2026-11-16" in user_message(_offre(), JOUR)
    assert "2027-01-02" in user_message(_offre(), date(2027, 1, 2))


def test_description_tronquee_a_6000():
    assert user_message(_offre(description="x" * 20000), JOUR).count("x") == 6000


def test_invariant_sans_pii_sur_la_fixture():
    for o in _offres():
        p = system_scoring() + user_message(o, JOUR)
        assert not TEL.search(p) and "@" not in p and "né le" not in p.lower()


def test_contacts_effaces_du_texte_offre():
    d = "Écrire à jean.dupont@exemple.fr ou appeler le 01 23 45 67 89 / 0123456789."
    m = user_message(_offre(description=d), JOUR)
    assert "@" not in m and not TEL.search(m)


# --- client Ollama ---
def _ollama(handler):
    return OllamaScorer(cfg.llm, httpx.Client(transport=httpx.MockTransport(handler)))


def _reponse(contenu: str):
    return httpx.Response(
        200,
        json={
            "message": {"content": contenu},
            "prompt_eval_count": 11,
            "eval_count": 7,
            "total_duration": 2.5e9,
        },
    )


def test_requete_ollama_suit_la_config():
    vues = []

    def handler(req):
        vues.append((str(req.url), json.loads(req.content)))
        return _reponse(_score(80).model_dump_json())

    score, usage = _ollama(handler).scorer(_offre(), JOUR)
    url, body = vues[0]
    c = cfg.llm.scoring
    assert url == "http://localhost:11434/api/chat"
    assert body["model"] == c.modele and body["stream"] is False and body["keep_alive"] == "10m"
    assert body["options"] == {"temperature": c.temperature, "seed": 42, "num_ctx": c.num_ctx}
    assert body["format"] == ScoreLLM.model_json_schema()
    assert [m["role"] for m in body["messages"]] == ["system", "user"]
    assert score.score == 80 and usage == Usage(11, 7, 2.5)


def test_score_hors_bornes_rejete():
    contenu = json.dumps(_score(80).model_dump() | {"score": 120})
    with pytest.raises(ScoreInvalide):
        _ollama(lambda req: _reponse(contenu)).scorer(_offre(), JOUR)


def test_json_invalide_rejete():
    with pytest.raises(ScoreInvalide):
        _ollama(lambda req: _reponse("pas du json")).scorer(_offre(), JOUR)


def test_connexion_refusee():
    def handler(req):
        raise httpx.ConnectError("refused")

    with pytest.raises(OllamaIndisponible):
        _ollama(handler).scorer(_offre(), JOUR)


# --- service ---
class Faux:
    def __init__(self, resultats=None):
        self.appels = 0
        self.resultats = resultats

    def scorer(self, offre, today):
        self.appels += 1
        r = self.resultats[self.appels - 1] if self.resultats else (_score(), Usage(10, 5, 1.0))
        if isinstance(r, Exception):
            raise r
        return r


@pytest.fixture
def session(tmp_path):
    url = f"sqlite:///{tmp_path / 's.db'}"
    migrer(url)
    with Session(make_engine(url)) as s:
        yield s


def _inserer(session, n):
    return [
        (repo.inserer_offre(session, o, cle_dedup=cle_dedup(o), now=NOW), o)
        for o in (_offre(source_id=str(i), url=f"u{i}", titre=f"Dev {i}") for i in range(n))
    ]


def _cfg(**llm):
    return cfg.model_copy(update={"llm": cfg.llm.model_copy(update=llm)})


def test_score_stocke_avec_tokens_et_secondes(session):
    offres = _inserer(session, 1)
    assert scorer_offres(session, offres, cfg, Faux(), NOW) == 1
    ligne = session.execute(text("select * from scores")).mappings().one()
    attendu = (cfg.llm.scoring.modele, 10, 5, 1.0)
    assert (ligne["modele"], ligne["prompt_tokens"], ligne["output_tokens"], ligne["duree_s"]) == attendu


def test_second_passage_sans_appel(session):
    offres = _inserer(session, 2)
    faux = Faux()
    scorer_offres(session, offres, cfg, faux, NOW)
    assert scorer_offres(session, offres, cfg, faux, NOW) == 0
    assert faux.appels == 2


def test_plafond_journalier(session):
    faux = Faux()
    assert scorer_offres(session, _inserer(session, 2), _cfg(llm_max_appels_jour=1), faux, NOW) == 1
    assert faux.appels == 1


def test_tentative_invalide_compte_dans_le_plafond(session):
    erreurs = []
    faux = Faux([ScoreInvalide("x")])
    offres = _inserer(session, 2)
    scorer_offres(session, offres, _cfg(llm_max_appels_jour=1), faux, NOW, erreurs=erreurs)
    assert faux.appels == 1 and len(erreurs) == 1
    # second run le même jour : plafond déjà atteint par la tentative invalide
    assert scorer_offres(session, offres, _cfg(llm_max_appels_jour=1), faux, NOW) == 0
    assert faux.appels == 1


def test_limite_de_duree_du_run(session):
    horloge = iter([0.0, 0.0, 600.0, 1000.0, 1000.0])
    faux = Faux()
    n = scorer_offres(
        session, _inserer(session, 3), _cfg(llm_max_duree_run_s=900), faux, NOW, chrono=lambda: next(horloge)
    )
    assert n == 2 and faux.appels == 2


def test_json_invalide_aucune_ligne_erreur_notee(session):
    erreurs = []
    offres = _inserer(session, 1)
    assert scorer_offres(session, offres, cfg, Faux([ScoreInvalide("json")]), NOW, erreurs=erreurs) == 0
    assert repo.lire_score(session, offres[0][0]) is None and len(erreurs) == 1
    assert scorer_offres(session, offres, cfg, Faux(), NOW) == 1  # retentée au run suivant


def test_ollama_indisponible_ne_plante_pas(session):
    erreurs = []
    faux = Faux([OllamaIndisponible("down")])
    assert scorer_offres(session, _inserer(session, 3), cfg, faux, NOW, erreurs=erreurs) == 0
    assert faux.appels == 1 and "ollama" in erreurs[0].lower()


# --- comparaison de modèles ---
def test_comparer_metriques():
    etiquettes = [
        {"offre": _offre().model_dump(mode="json"), "score_attendu": 80},
        {"offre": _offre(titre="b").model_dump(mode="json"), "score_attendu": 40},
        {"offre": _offre(titre="c").model_dump(mode="json"), "score_attendu": None},
    ]

    class S:
        def scorer(self, o, today):
            return _score(70), Usage(1, 1, 2.0)

    m = comparer(etiquettes, S(), JOUR)
    assert m == {"n": 2, "ecart_moyen": 20.0, "franchissements": 1, "secondes": 4.0, "ignorees": 1}


def test_scorer_factice_respecte_le_protocole():
    assert ScorerFactice().scorer(_offre(), JOUR)[0].score == 50


def test_prompt_ne_penalise_pas_une_fourchette_incluant_bac3():
    s = system_scoring()
    assert "fourchette" in s and "plus haut niveau accepté" in s
    assert "plus haut niveau accepté" in user_message(_offre(), JOUR)
