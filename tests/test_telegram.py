import json
from datetime import UTC, date, datetime
from pathlib import Path

import httpx
import pytest
from sqlalchemy.orm import Session

from denicheur.config import load_config
from denicheur.db import repo
from denicheur.db.base import make_engine, migrer
from denicheur.messages_fr import RIEN_DE_NEUF, format_offre
from denicheur.models import Offre, Piste, ScoreLLM
from denicheur.pipeline.dedupe import cle_dedup
from denicheur.telegram.api import TelegramAPI, TelegramError
from denicheur.telegram.digest import envoyer_digest, envoyer_test

RACINE = Path(__file__).parent.parent
cfg = load_config(RACINE / "config" / "recherches.yaml")
NOW = datetime(2026, 11, 16, 9, tzinfo=UTC)
TOKEN = "123:SECRET"


def _offre(**kw):
    base = {
        "source": "t", "source_id": "1", "url": "https://x.fr/itic", "titre": "Développeur de sécurité",
        "entreprise": "ITIC PARIS", "commune": "Paris", "lat": 48.85, "lon": 2.39,
        "piste": Piste.ALTERNANCE, "duree_mois": 6, "debut": None, "debut_des_que_possible": True,
        "niveau_diplome": "7", "description": "d", "publiee_le": NOW, "expire_le": None, "distance_km": 23.2,
    }  # fmt: skip
    return Offre(**{**base, **kw})


def _score(n=74, **kw):
    base = {
        "score": n, "type": "alternance", "points_forts": ["Sécurité des SI", "Python"],
        "points_faibles": ["Peu de développement"], "alerte": "Niveau demandé : Bac+5",
        "projet_a_citer": "RiftMind", "resume": "r",
    }  # fmt: skip
    return ScoreLLM(**{**base, **kw})


def _api(vues, chat_id="42", sleeps=None):
    def handler(req):
        vues.append((str(req.url), json.loads(req.content or b"{}")))
        return httpx.Response(200, json={"ok": True, "result": []})

    http = httpx.Client(transport=httpx.MockTransport(handler))
    return TelegramAPI(
        TOKEN, http, chat_id=chat_id, sleep=(sleeps.append if sleeps is not None else lambda s: None)
    )


# --- messages ---
ITIC = """\
<b>Développeur de sécurité</b>
🏢 ITIC PARIS · 📍 Paris (23 km)
🕒 6 mois · début : dès que possible
⭐ Score 74/100
✅ Sécurité des SI, Python
➖ Peu de développement
⚠️ Niveau demandé : Bac+5
💡 Projet à citer : RiftMind
🔗 <a href="https://x.fr/itic">Voir l'offre</a>"""


def test_message_itic_de_reference():
    assert format_offre(_offre(), _score()) == ITIC


def test_alerte_immediate_et_lieu_a_verifier():
    m = format_offre(_offre(lieu_a_verifier=True, distance_km=None), _score(alerte=None), alerte=True)
    assert m.startswith("🚨 Alternance · <b>")
    assert "📍 lieu à vérifier" in m and "km" not in m and "⚠️" not in m


def test_debut_stage_en_francais():
    m = format_offre(_offre(piste=Piste.STAGE, duree_mois=6, debut=date(2027, 2, 1),
                            debut_des_que_possible=False), _score())  # fmt: skip
    assert "🕒 6 mois · début : février 2027" in m


def test_html_echappe():
    m = format_offre(_offre(titre="<script>x</script>", entreprise="A&B"), _score())
    assert "&lt;script&gt;" in m and "<script>" not in m and "A&amp;B" in m


def test_trois_elements_max_et_limite_4096():
    long = "y" * 5000
    m = format_offre(_offre(titre=long), _score(points_forts=[long, "b", "c", "d"], alerte=long))
    assert len(m) <= 4096 and m.split("✅ ")[1].split("\n")[0].count(", ") == 2
    assert m.count("<b>") == m.count("</b>") == 1


# --- API ---
def test_envoi_vers_le_chat_configure():
    vues = []
    _api(vues).send_message("salut")
    url, body = vues[0]
    assert url == f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    assert body["chat_id"] == "42" and body["text"] == "salut" and body["parse_mode"] == "HTML"


def test_aucun_envoi_sans_chat():
    with pytest.raises(TelegramError):
        _api([], chat_id=None).send_message("x")
    with pytest.raises(TypeError):
        _api([]).send_message("x", chat_id="99")  # type: ignore[call-arg]


def test_pause_entre_envois():
    pauses = []
    api = _api([], sleeps=pauses)
    api.send_message("a")
    api.send_message("b")
    assert pauses == [1]


def test_erreur_http_sans_fuite_du_token():
    http = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(401, json={"ok": False})))
    with pytest.raises(TelegramError) as e:
        TelegramAPI(TOKEN, http, chat_id="1").send_message("x")
    assert "SECRET" not in str(e.value) and e.value.__suppress_context__  # la cause httpx porte l'URL


# --- digest ---
@pytest.fixture
def session(tmp_path):
    url = f"sqlite:///{tmp_path / 't.db'}"
    migrer(url)
    with Session(make_engine(url)) as s:
        yield s


def _stocker(session, i, n, **kw):
    o = _offre(source_id=str(i), url=f"https://x.fr/{i}", titre=f"Dev {i}", **kw)
    oid = repo.inserer_offre(session, o, cle_dedup=cle_dedup(o), now=NOW)
    repo.inserer_score(
        session, oid, _score(n), modele="m", prompt_tokens=1, output_tokens=1, duree_s=1, now=NOW
    )
    return oid


def test_digest_top_10_par_score_decroissant(session):
    for i in range(12):
        _stocker(session, i, 65 + i)
    _stocker(session, 99, 64)  # sous le seuil
    vues = []
    assert envoyer_digest(session, _api(vues), cfg, NOW) == 10
    textes = [b["text"] for _, b in vues]
    assert len(textes) == 11  # en-tête + 10 offres
    assert [t.split("\n")[0] for t in textes[1:4]] == ["<b>Dev 11</b>", "<b>Dev 10</b>", "<b>Dev 9</b>"]
    assert repo.offres_a_notifier(session, 65, 20)[0][1].titre in {"Dev 0", "Dev 1"}


def test_digest_respecte_le_score_min(session):
    _stocker(session, 1, 64)
    _stocker(session, 2, 65)
    vues = []
    assert envoyer_digest(session, _api(vues), cfg, NOW) == 1
    assert "Dev 2" in vues[1][1]["text"]


def test_digest_ne_renvoie_pas_et_ignore_les_rejetees(session):
    _stocker(session, 1, 90)
    vues = []
    envoyer_digest(session, _api(vues), cfg, NOW)
    vues.clear()
    envoyer_digest(session, _api(vues), cfg, NOW)
    assert [b["text"] for _, b in vues] == [RIEN_DE_NEUF]


def test_digest_vide(session):
    vues = []
    assert envoyer_digest(session, _api(vues), cfg, NOW) == 0
    assert [b["text"] for _, b in vues] == ["Rien de nouveau aujourd'hui"]


def test_digest_test_envoie_une_offre_factice():
    vues = []
    envoyer_test(_api(vues))
    assert len(vues) == 1 and "TEST" in vues[0][1]["text"]
