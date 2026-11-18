import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from denicheur.clock import heure_atteinte, is_daytime
from denicheur.config import load_config
from denicheur.db import repo
from denicheur.db.base import make_engine, migrer
from denicheur.models import ScoreLLM, Statut
from denicheur.pipeline.run import Deps, executer
from denicheur.scoring.llm import OllamaIndisponible, Usage
from denicheur.sources.adzuna import collecter as collecter_adzuna
from denicheur.sources.la_bonne_alternance import collecter
from denicheur.telegram.api import TelegramAPI

RACINE = Path(__file__).parent.parent
FIXTURE = json.loads((RACINE / "tests" / "fixtures" / "lba_search.json").read_text(encoding="utf-8"))
cfg = load_config(RACINE / "config" / "recherches.yaml")
# 10:00 Paris (UTC+1 en novembre)
T0 = datetime(2026, 11, 16, 9, tzinfo=UTC)


class Scorer:
    def __init__(self, exception_apres=None):
        self.appels = 0
        self.exception_apres = exception_apres

    def scorer(self, offre, today):
        self.appels += 1
        if self.exception_apres is not None and self.appels > self.exception_apres[0]:
            raise self.exception_apres[1]
        n = 85 if "WOODOO" in (offre.entreprise or "") else 70
        s = ScoreLLM(
            score=n, type="alternance", points_forts=["a"], points_faibles=[], alerte=None,
            projet_a_citer="RiftMind", resume="r",
        )  # fmt: skip
        return s, Usage(1, 1, 1.0)


class Env:
    def __init__(self, tmp_path):
        url = f"sqlite:///{tmp_path / 'r.db'}"
        migrer(url)
        self.session = Session(make_engine(url))
        self.envoyes = []
        self.corps = []
        self.collectes = 0
        client = httpx.Client(
            transport=httpx.MockTransport(lambda r: httpx.Response(200, json=FIXTURE)),
            headers={"Authorization": "Bearer k"},
        )

        def source(config, now):
            self.collectes += 1
            return collecter(config, client, now)

        self.source = source

        def envoi(req):
            corps = json.loads(req.content)
            self.corps.append(corps)
            self.envoyes.append(corps["text"])
            return httpx.Response(200, json={"ok": True, "result": {}})

        self.api = TelegramAPI("t", httpx.Client(transport=httpx.MockTransport(envoi)), chat_id="1",
                               sleep=lambda s: None)  # fmt: skip

    def run(
        self,
        now,
        mode="auto",
        scorer=None,
        sources=None,
        api="defaut",
        sources_stage=None,
        entreprises=None,
        config=None,
    ):
        deps = Deps(
            self.session,
            config or cfg,
            {"lba": self.source} if sources is None else sources,
            scorer or Scorer(),
            self.api if api == "defaut" else api,
            sources_stage=sources_stage or {},
            actualiser_entreprises=entreprises,
        )
        return executer(mode, deps, now)

    def ligne(self):
        ligne = dict(
            self.session.execute(text("select * from executions order by id desc")).mappings().first()
        )
        ligne["erreurs"] = json.loads(ligne["erreurs"])  # JSON stocké en texte
        return ligne


@pytest.fixture
def env(tmp_path):
    e = Env(tmp_path)
    yield e
    e.session.close()


# --- horloge ---
def test_plage_horaire_aux_bornes():
    def paris(h, m):  # novembre : Paris = UTC+1
        return datetime(2026, 11, 16, h - 1, m, tzinfo=UTC)

    assert [is_daytime(paris(h, m)) for h, m in [(7, 0), (8, 0), (8, 31), (19, 59), (20, 0)]] == [
        False, True, True, True, False,
    ]  # fmt: skip
    assert not heure_atteinte(paris(8, 29), "08:30") and heure_atteinte(paris(8, 31), "08:30")


# --- run ---
def test_run_nominal_alerte_puis_digest_sans_doublon(env):
    b = env.run(T0)
    assert b.ok and (b.collectees, b.retenues, b.scorees, b.notifiees) == (16, 2, 2, 2)
    ligne = env.ligne()
    assert (ligne["offres_collectees"], ligne["offres_retenues"], ligne["offres_scorees"]) == (16, 2, 2)
    assert ligne["offres_notifiees"] == 2 and ligne["fin"] is not None and ligne["duree_llm_s"] >= 0
    alerte, entete, digest = env.envoyes
    assert alerte.startswith("🚨 Alternance") and "Score 85" in alerte
    assert "1 offre" in entete and "Score 70" in digest and "Score 85" not in digest
    env.envoyes.clear()
    env.run(T0 + timedelta(hours=4))
    assert env.envoyes == []  # rien de renvoyé, digest déjà parti aujourd'hui


def test_pas_de_recollecte_sous_3h(env):
    env.run(T0)
    env.run(T0 + timedelta(hours=2))
    assert env.collectes == 1
    env.run(T0 + timedelta(hours=3))
    assert env.collectes == 2


def test_avant_8h_rien_n_est_envoye(env):
    env.run(T0, scorer=Scorer(), api=None)  # collecte + notation, sans envoi
    nuit = datetime(2026, 11, 17, 6, tzinfo=UTC)  # 07:00 Paris
    env.run(nuit)
    assert env.envoyes == [] and env.collectes == 1
    env.run(datetime(2026, 11, 17, 7, 31, tzinfo=UTC))  # 08:31 Paris
    assert len(env.envoyes) == 3  # alerte Woodoo, en-tête, ITIC
    env.run(datetime(2026, 11, 17, 7, 45, tzinfo=UTC))
    assert len(env.envoyes) == 3


def test_pause_collecte_et_note_sans_envoyer(env):
    repo.set_param(env.session, "pause", "1")
    b = env.run(T0)
    assert env.envoyes == [] and b.scorees == 2 and b.notifiees == 0


def test_dry_run_sans_api_n_envoie_rien(env):
    b = env.run(T0, api=None)
    assert b.ok and b.notifiees == 0 and b.retenues == 2
    assert (
        env.session.execute(text("select count(*) from offres where notifiee_le is not null")).scalar() == 0
    )


def test_source_en_erreur_consignee_sans_arreter_le_run(env):
    def casse(config, now):
        raise RuntimeError("API HS")

    b = env.run(T0, sources={"casse": casse, "lba": env.source})
    assert b.ok and b.retenues == 2
    assert any("casse" in e for e in env.ligne()["erreurs"])


def test_ollama_injoignable_les_offres_deja_notees_partent(env):
    b = env.run(T0, scorer=Scorer(exception_apres=(1, OllamaIndisponible("down"))))
    assert b.ok and b.scorees == 1
    assert any("ollama" in e.lower() for e in env.ligne()["erreurs"])
    assert any("Score 70" in m for m in env.envoyes)


def test_echec_non_gere_message_sans_trace_et_code_1(env):
    b = env.run(T0, scorer=Scorer(exception_apres=(0, RuntimeError("secret-boom"))))
    assert not b.ok
    assert env.envoyes == ["⚠️ La collecte du jour a échoué : RuntimeError"]
    assert "secret-boom" not in json.dumps(env.ligne()["erreurs"])
    assert env.ligne()["fin"] is not None


def test_un_stage_bien_note_attend_le_digest(env):
    from denicheur.models import Offre, Piste
    from denicheur.pipeline.dedupe import cle_dedup

    o = Offre(
        source="t", source_id="s", url="u", titre="Stage IA", entreprise="X", commune="Paris", lat=None,
        lon=None, piste=Piste.STAGE, duree_mois=6, debut=None, niveau_diplome=None, description="d",
        publiee_le=None, expire_le=None,
    )  # fmt: skip
    oid = repo.inserer_offre(env.session, o, cle_dedup=cle_dedup(o), now=T0)
    s = Scorer().scorer(o, T0.date())[0].model_copy(update={"score": 90, "type": "stage"})
    repo.inserer_score(env.session, oid, s, modele="m", prompt_tokens=1, output_tokens=1, duree_s=1, now=T0)
    env.run(T0, sources={})
    assert not env.envoyes[0].startswith("🚨") and "Stage IA" in env.envoyes[1]


def test_fin_d_execution_est_l_heure_reelle(env):
    fin = T0 + timedelta(minutes=5)
    deps = Deps(env.session, cfg, {}, Scorer(), None, maintenant=lambda: fin)
    executer("auto", deps, T0)
    assert env.ligne()["fin"].startswith("2026-11-16 09:05")


# --- stage (Adzuna) ---
ADZUNA = json.loads((RACINE / "tests" / "fixtures" / "adzuna_search.json").read_text(encoding="utf-8"))


class SourceStage:
    """Source Adzuna réelle (fixture) qui compte ses collectes."""

    def __init__(self, erreur=None):
        self.collectes = 0
        self.erreur = erreur
        self.client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=ADZUNA)))

    def __call__(self, config, now):
        self.collectes += 1
        if self.erreur:
            raise self.erreur
        return collecter_adzuna(config, self.client, now, "id", "cle", sleep=lambda s: None)

    @property
    def dict(self):
        return {"adzuna": self}


def test_stage_collecte_une_fois_par_jour(env):
    stage = SourceStage()
    env.run(T0, sources_stage=stage.dict)
    assert stage.collectes == 1
    assert repo.get_param(env.session, "derniere_collecte:stage") == "2026-11-16"
    env.run(T0 + timedelta(hours=3), sources_stage=stage.dict)
    assert stage.collectes == 1  # déjà fait aujourd'hui
    env.run(T0 + timedelta(days=1), sources_stage=stage.dict)
    assert stage.collectes == 2  # nouveau jour


def test_stage_hors_plage_horaire_pas_collecte_en_auto(env):
    stage = SourceStage()
    env.run(datetime(2026, 11, 16, 6, tzinfo=UTC), sources_stage=stage.dict)  # 07:00 Paris
    env.run(datetime(2026, 11, 16, 19, tzinfo=UTC), sources_stage=stage.dict)  # 20:00 Paris
    assert stage.collectes == 0


def test_mode_stage_force_la_collecte_de_stage_seule(env):
    stage = SourceStage()
    env.run(T0, sources_stage=stage.dict)
    nuit = datetime(2026, 11, 16, 23, 30, tzinfo=UTC)  # 00:30 Paris, le lendemain
    env.run(nuit, mode="stage", sources_stage=stage.dict)
    assert stage.collectes == 2 and env.collectes == 1  # l'alternance n'est pas refaite
    assert repo.get_param(env.session, "derniere_collecte:stage") == "2026-11-17"  # date de Paris


def test_mode_alternance_ne_collecte_pas_le_stage(env):
    stage = SourceStage()
    env.run(T0, mode="alternance", sources_stage=stage.dict)
    assert env.collectes == 1 and stage.collectes == 0
    assert repo.get_param(env.session, "derniere_collecte:stage") is None


def test_sans_source_de_stage_aucune_trace_de_collecte(env):
    env.run(T0, mode="stage")
    assert repo.get_param(env.session, "derniere_collecte:stage") is None


def test_offres_de_stage_retenues_et_notees(env):
    b = env.run(T0, mode="stage", sources_stage=SourceStage().dict, api=None)
    assert b.ok and b.collectees == 50 and b.retenues > 40 and b.scorees == b.retenues
    assert env.collectes == 0


def test_erreur_stage_isolee_et_sans_cle(env):
    stage = SourceStage(erreur=RuntimeError("https://api.adzuna.com/?app_key=SECRET"))
    b = env.run(T0, sources_stage=stage.dict)
    assert b.ok and b.collectees == 16  # l'alternance est collectée normalement
    assert b.erreurs == ["source adzuna : RuntimeError"]
    assert "SECRET" not in json.dumps(env.ligne()["erreurs"])


def test_run_auto_cumule_alternance_et_stage(env):
    b = env.run(T0, sources_stage=SourceStage().dict, api=None)
    assert (b.collectees, b.retenues) == (16 + 50, 2 + 45)
    ligne = env.ligne()
    assert (ligne["offres_collectees"], ligne["offres_retenues"]) == (66, 47)


# --- boutons et rappel J+7 ---
def test_alerte_instantanee_porte_les_boutons_de_l_offre(env):
    env.run(T0)
    alerte = env.corps[0]
    assert alerte["text"].startswith("🚨 Alternance")
    donnees = [b["callback_data"] for ligne in alerte["reply_markup"]["inline_keyboard"] for b in ligne]
    assert [d[0] for d in donnees] == ["p", "b", "r", "x", "d"] and len(
        {d.split(":")[1] for d in donnees}
    ) == 1


def _candidature_envoyee_le(env, jour):
    """Premier run (collecte + envois), puis une candidature marquée envoyée à `jour`."""
    env.run(T0)
    oid = (
        env.session.execute(text("select id from offres where motif_rejet is null order by id"))
        .scalars()
        .first()
    )
    repo.marquer(env.session, oid, Statut.CANDIDATURE_ENVOYEE, jour)
    env.session.commit()
    env.envoyes.clear()
    return oid


def _rappels(env):
    return [t for t in env.envoyes if t.startswith("⏰")]


def test_rappel_a_j_plus_7_une_seule_fois(env):
    _candidature_envoyee_le(env, T0)
    env.run(T0 + timedelta(days=7))
    (rappel,) = _rappels(env)
    assert "7 jours" in rappel
    assert repo.candidatures_a_relancer(env.session, (T0 + timedelta(days=7)).date()) == []
    env.run(T0 + timedelta(days=7, hours=4))
    env.run(T0 + timedelta(days=8))
    assert len(_rappels(env)) == 1


def test_rappel_porte_le_bouton_relance_de_l_offre(env):
    oid = _candidature_envoyee_le(env, T0)
    env.corps.clear()
    env.run(T0 + timedelta(days=7))
    (rappel,) = [c for c in env.corps if c["text"].startswith("⏰")]
    boutons = [b for ligne in rappel["reply_markup"]["inline_keyboard"] for b in ligne]
    assert boutons == [{"text": "✉️ Relance", "callback_data": f"l:{oid}"}]


def test_pas_de_rappel_a_j_plus_6(env):
    _candidature_envoyee_le(env, T0)
    env.run(T0 + timedelta(days=6))
    assert _rappels(env) == []


def test_pause_supprime_le_rappel_sans_le_consommer(env):
    _candidature_envoyee_le(env, T0)
    repo.set_param(env.session, "pause", "1")
    env.run(T0 + timedelta(days=7))
    assert _rappels(env) == []
    repo.set_param(env.session, "pause", "0")
    env.run(T0 + timedelta(days=7, hours=1))
    assert len(_rappels(env)) == 1


def test_pas_de_rappel_la_nuit_il_part_le_matin(env):
    _candidature_envoyee_le(env, T0)
    env.run(datetime(2026, 11, 23, 6, tzinfo=UTC))  # 07:00 Paris
    assert _rappels(env) == []
    env.run(datetime(2026, 11, 23, 7, 30, tzinfo=UTC))  # 08:30 Paris
    assert len(_rappels(env)) == 1


def test_echec_d_envoi_laisse_la_candidature_due(env):
    _candidature_envoyee_le(env, T0)
    api = TelegramAPI("t", httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500))),
                      chat_id="1", sleep=lambda s: None)  # fmt: skip
    assert not env.run(T0 + timedelta(days=7), api=api).ok
    assert len(repo.candidatures_a_relancer(env.session, (T0 + timedelta(days=7)).date())) == 1


# --- actualisation quotidienne des entreprises ---
class Entreprises:
    def __init__(self, erreurs=None, exception=None):
        self.appels = []
        self.erreurs = erreurs or []
        self.exception = exception

    def __call__(self, session, config, now):
        self.appels.append(now)
        if self.exception:
            raise self.exception
        return list(self.erreurs)


def test_entreprises_actualisees_une_fois_par_jour(env):
    ent = Entreprises()
    env.run(T0, entreprises=ent)
    assert len(ent.appels) == 1
    assert repo.get_param(env.session, "derniere_actualisation:entreprises") == "2026-11-16"
    env.run(T0 + timedelta(hours=3), entreprises=ent)
    assert len(ent.appels) == 1
    env.run(T0 + timedelta(days=1), entreprises=ent)
    assert len(ent.appels) == 2


def test_entreprises_hors_plage_horaire_pas_actualisees(env):
    ent = Entreprises()
    env.run(datetime(2026, 11, 16, 6, tzinfo=UTC), entreprises=ent)  # 07:00 Paris
    env.run(datetime(2026, 11, 16, 19, tzinfo=UTC), entreprises=ent)  # 20:00 Paris
    assert ent.appels == []
    assert repo.get_param(env.session, "derniere_actualisation:entreprises") is None


@pytest.mark.parametrize("mode", ["alternance", "stage", "digest"])
def test_entreprises_seulement_en_mode_auto(env, mode):
    ent = Entreprises()
    env.run(T0, mode=mode, entreprises=ent)
    assert ent.appels == []


def test_sans_actualisation_configuree_aucune_trace(env):
    env.run(T0)
    assert repo.get_param(env.session, "derniere_actualisation:entreprises") is None


def test_erreurs_des_entreprises_consignees_sans_bloquer_le_run(env):
    ent = Entreprises(erreurs=["recherche entreprises 78 62.01Z : ErreurRecherche"])
    b = env.run(T0, entreprises=ent)
    assert b.ok and "recherche entreprises 78 62.01Z : ErreurRecherche" in b.erreurs
    assert "ErreurRecherche" in str(env.ligne()["erreurs"])
    assert b.collectees > 0 and b.scorees > 0
    assert repo.get_param(env.session, "derniere_actualisation:entreprises") == "2026-11-16"


def test_exception_des_entreprises_isolee(env):
    ent = Entreprises(exception=RuntimeError("secret"))
    b = env.run(T0, entreprises=ent)
    assert b.ok and "entreprises : RuntimeError" in b.erreurs and "secret" not in str(b.erreurs)
    assert b.collectees > 0


# --- liste du jour des entreprises ---
DIGEST = datetime(2026, 11, 17, 7, 31, tzinfo=UTC)  # 08:31 Paris


def _entreprises(env, n, depart=1):
    from denicheur.models import Entreprise

    for i in range(depart, depart + n):
        e = Entreprise(siret=f"{i:09d}00011", nom=f"SOC{i}", priorite=i, distance_km=float(i), origine="csv")
        repo.enregistrer_entreprise(env.session, e, T0)
    env.session.commit()


def _messages_entreprises(env):
    return [(c["text"], c.get("reply_markup")) for c in env.corps if c["text"].startswith("🏢")]


def _donnees(clavier):
    return [b["callback_data"] for ligne in clavier["inline_keyboard"] for b in ligne]


def test_liste_du_jour_apres_le_digest_dix_entreprises_avec_leurs_boutons(env):
    _entreprises(env, 25)
    env.run(DIGEST, sources={})
    assert env.envoyes[0] == "Rien de nouveau aujourd'hui"
    assert env.envoyes[1] == "🏢 10 entreprises à démarcher aujourd'hui"
    messages = _messages_entreprises(env)[1:]  # le premier est l'en-tête
    assert len(messages) == 10
    assert [m[0].split("\n")[0] for m in messages] == [f"🏢 <b>SOC{i}</b>" for i in range(1, 11)]
    assert _donnees(messages[0][1]) == ["s:1", "t:1", "e:1", "i:1"]
    assert _donnees(messages[9][1]) == ["s:10", "t:10", "e:10", "i:10"]
    assert repo.get_param(env.session, "derniere_liste_entreprises") == "2026-11-17"
    assert repo.nb_listees_le(env.session, datetime(2026, 11, 17).date()) == 10
    assert len(repo.entreprises_du_jour(env.session, 100)) == 15


def test_liste_une_seule_fois_par_jour_puis_dix_nouvelles_le_lendemain(env):
    _entreprises(env, 25)
    env.run(DIGEST, sources={})
    env.corps.clear()
    env.run(DIGEST + timedelta(hours=1), sources={})
    assert _messages_entreprises(env) == []
    env.run(DIGEST + timedelta(days=1), sources={})
    suivants = [m[0].split("\n")[0] for m in _messages_entreprises(env)[1:]]
    assert suivants == [f"🏢 <b>SOC{i}</b>" for i in range(11, 21)]  # jamais deux fois la même


def test_pas_de_liste_avant_l_heure_du_digest(env):
    _entreprises(env, 3)
    env.run(datetime(2026, 11, 17, 6, 59, tzinfo=UTC), sources={})  # 07:59 Paris
    assert _messages_entreprises(env) == []
    assert repo.get_param(env.session, "derniere_liste_entreprises") is None


def test_mode_digest_envoie_la_liste(env):
    _entreprises(env, 3)
    env.run(T0, mode="digest", sources={})
    assert len(_messages_entreprises(env)) == 4


def test_pause_aucune_entreprise_envoyee_ni_marquee(env):
    _entreprises(env, 3)
    repo.set_param(env.session, "pause", "1")
    env.run(DIGEST, sources={})
    assert env.envoyes == []
    assert len(repo.entreprises_du_jour(env.session, 100)) == 3


def test_dry_run_aucune_entreprise_marquee(env):
    _entreprises(env, 3)
    env.run(DIGEST, sources={}, api=None)
    assert len(repo.entreprises_du_jour(env.session, 100)) == 3


def test_rien_d_eligible_aucun_message_puis_liste_des_qu_il_y_en_a(env):
    env.run(DIGEST, sources={})
    assert _messages_entreprises(env) == []
    assert repo.get_param(env.session, "derniere_liste_entreprises") is None
    _entreprises(env, 2)
    env.run(DIGEST + timedelta(hours=1), sources={})
    assert len(_messages_entreprises(env)) == 3


def test_entreprises_contactees_ou_ecartees_jamais_listees(env):
    _entreprises(env, 4)
    repo.marquer_entreprise(env.session, 1, Statut.CANDIDATURE_ENVOYEE, T0)
    repo.marquer_entreprise(env.session, 2, Statut.IGNOREE, T0)
    env.session.commit()
    env.run(DIGEST, sources={})
    noms = [m[0].split("\n")[0] for m in _messages_entreprises(env)[1:]]
    assert noms == ["🏢 <b>SOC3</b>", "🏢 <b>SOC4</b>"]


def test_echec_en_cours_de_liste_pas_de_renvoi_et_reprise_du_reste(env):
    _entreprises(env, 25)
    envois = []

    def handler(req):
        envois.append(json.loads(req.content)["text"])
        if len(envois) == 6:  # digest + en-tête + trois entreprises passent, la quatrième échoue
            return httpx.Response(500, json={"ok": False})
        return httpx.Response(200, json={"ok": True, "result": {}})

    api = TelegramAPI(
        "t", httpx.Client(transport=httpx.MockTransport(handler)), chat_id="1", sleep=lambda s: None
    )
    b = env.run(DIGEST, sources={}, api=api)
    assert not b.ok
    assert repo.nb_listees_le(env.session, datetime(2026, 11, 17).date()) == 3
    assert repo.get_param(env.session, "derniere_liste_entreprises") is None
    env.corps.clear()
    env.run(DIGEST + timedelta(hours=1), sources={})
    reprise = [m[0].split("\n")[0] for m in _messages_entreprises(env)]
    assert reprise[0] == "🏢 7 entreprises à démarcher aujourd'hui"
    assert reprise[1:] == [f"🏢 <b>SOC{i}</b>" for i in range(4, 11)]  # ni renvoi des trois, ni plus de dix
    assert repo.nb_listees_le(env.session, datetime(2026, 11, 17).date()) == 10


def test_message_d_entreprise_mentionne_l_offre_ouverte_de_meme_siret(env):
    from denicheur.models import Offre, Piste

    _entreprises(env, 1)
    o = Offre(
        source="t", source_id="1", url="https://x/1", titre="Alternance dev web", entreprise="SOC1",
        siret="000000001" "00011", commune="Paris", lat=None, lon=None, piste=Piste.ALTERNANCE,
        duree_mois=None, debut=None, niveau_diplome=None, description="d", publiee_le=None, expire_le=None,
    )  # fmt: skip
    repo.inserer_offre(env.session, o, cle_dedup="k", now=T0)
    env.session.commit()
    env.run(DIGEST, sources={})
    assert "📌 Offre ouverte aussi : Alternance dev web" in _messages_entreprises(env)[1][0]


def test_liste_par_jour_a_zero_aucune_liste_et_rien_de_marque(env):
    _entreprises(env, 5)
    sans_liste = cfg.model_copy(
        update={"entreprises": cfg.entreprises.model_copy(update={"liste_par_jour": 0})}
    )
    env.run(DIGEST, sources={}, config=sans_liste)
    assert _messages_entreprises(env) == []
    assert repo.get_param(env.session, "derniere_liste_entreprises") is None
    assert len(repo.entreprises_du_jour(env.session, 100)) == 5
    env.run(DIGEST + timedelta(hours=1), sources={})  # réactivée : la liste part
    assert len(_messages_entreprises(env)) == 6
