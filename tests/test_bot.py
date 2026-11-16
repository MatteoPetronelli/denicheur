from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from denicheur.config import load_config
from denicheur.db import repo
from denicheur.db.base import make_engine, migrer
from denicheur.db.tables import candidatures
from denicheur.models import Offre, Piste, Statut
from denicheur.telegram.api import TelegramError
from denicheur.telegram.bot import BotDeps, boucle
from denicheur.telegram.keyboard import clavier_envoyee

CONFIG = load_config("config/recherches.yaml")
NOW = datetime(2026, 11, 16, 9, 0, tzinfo=UTC)
CHAT = "4242"


class FauxAPI:
    """Rejoue des réponses de getUpdates et note tous les appels."""

    def __init__(self, *paquets, echec_envoi=None):
        self.paquets = list(paquets)
        self.appels: list[tuple] = []
        self.echec_envoi = echec_envoi

    def delete_webhook(self):
        self.appels.append(("delete_webhook",))
        return True

    def get_updates(self, offset=None, timeout=0):
        self.appels.append(("get_updates", offset, timeout))
        paquet = self.paquets.pop(0) if self.paquets else []
        if isinstance(paquet, Exception):
            raise paquet
        return paquet

    def send_message(self, texte, reply_markup=None):
        self.appels.append(("send_message", texte, reply_markup))
        if self.echec_envoi:
            raise self.echec_envoi
        return {}

    def answer_callback(self, callback_id, texte=None):
        self.appels.append(("answer_callback", callback_id, texte))

    def edit_keyboard(self, message_id, reply_markup):
        self.appels.append(("edit_keyboard", message_id, reply_markup))

    def de_type(self, nom):
        return [a for a in self.appels if a[0] == nom]


@pytest.fixture
def session(tmp_path):
    url = f"sqlite:///{tmp_path / 'test.db'}"
    migrer(url)
    with Session(make_engine(url)) as s:
        yield s


def _offre(session, n=1):
    offre = Offre(
        source="lba", source_id=str(n), url=f"https://x/{n}", titre=f"Dev {n}", entreprise="ACME",
        commune="Paris", lat=None, lon=None, piste=Piste.ALTERNANCE, duree_mois=None, debut=None,
        niveau_diplome=None, description="d", publiee_le=None, expire_le=None,
    )  # fmt: skip
    oid = repo.inserer_offre(session, offre, cle_dedup=f"k{n}", now=NOW)
    session.commit()  # comme en vrai : le bot ne voit que des offres déjà enregistrées
    return oid


def _bouton(uid, data, *, chat=CHAT, auteur=CHAT, message_id=7):
    return {
        "update_id": uid,
        "callback_query": {
            "id": f"cb{uid}", "from": {"id": int(auteur)}, "data": data,
            "message": {"message_id": message_id, "chat": {"id": int(chat)}},
        },
    }  # fmt: skip


def _message(uid, texte, *, chat=CHAT):
    return {"update_id": uid, "message": {"message_id": 1, "chat": {"id": int(chat)}, "text": texte}}


def _lancer(session, api, tours=1):
    restants = iter([True] * tours)
    pauses: list[float] = []
    deps = BotDeps(api, session, CONFIG, CHAT, lambda: NOW)
    boucle(deps, sleep=pauses.append, continuer=lambda: next(restants, False))
    return pauses


def _statut(session, oid):
    return repo.statut_de(session, oid)


def test_demarrage_supprime_le_webhook_une_fois_et_interroge_en_long_polling(session):
    api = FauxAPI([], [])
    _lancer(session, api, tours=2)
    assert api.de_type("delete_webhook") == [("delete_webhook",)]
    assert api.de_type("get_updates") == [("get_updates", None, 50), ("get_updates", None, 50)]


def test_echec_du_webhook_n_arrete_pas_la_boucle(session):
    api = FauxAPI([])
    api.delete_webhook = lambda: (_ for _ in ()).throw(TelegramError("x"))
    _lancer(session, api)
    assert api.de_type("get_updates")


def test_je_postule_met_a_jour_la_base_repond_et_change_le_clavier(session):
    oid = _offre(session)
    api = FauxAPI([_bouton(10, f"p:{oid}", message_id=33)])
    _lancer(session, api)
    assert _statut(session, oid) is Statut.CANDIDATURE_ENVOYEE
    assert api.de_type("answer_callback") == [("answer_callback", "cb10", "✅ Candidature notée")]
    assert api.de_type("edit_keyboard") == [("edit_keyboard", 33, clavier_envoyee())]
    ligne = session.execute(select(candidatures)).mappings().one()
    assert ligne["envoyee_le"] == datetime(2026, 11, 16, 9, 0)


def test_je_postule_deux_fois_ne_change_rien_et_repond(session):
    oid = _offre(session)
    api = FauxAPI([_bouton(10, f"p:{oid}"), _bouton(11, f"p:{oid}")])
    _lancer(session, api)
    assert [a[2] for a in api.de_type("answer_callback")] == [
        "✅ Candidature notée",
        "Déjà notée comme envoyée.",
    ]
    assert len(api.de_type("edit_keyboard")) == 1


def test_transition_refusee_repond_sans_modifier_la_base(session):
    oid = _offre(session)
    repo.marquer(session, oid, Statut.IGNOREE, NOW)
    session.commit()
    api = FauxAPI([_bouton(10, f"p:{oid}")])
    _lancer(session, api)
    assert _statut(session, oid) is Statut.IGNOREE
    (reponse,) = api.de_type("answer_callback")
    assert "Impossible" in reponse[2]
    assert api.de_type("edit_keyboard") == []


def test_offre_inconnue_repond_sans_ecrire(session):
    api = FauxAPI([_bouton(10, "p:999")])
    _lancer(session, api)
    assert session.execute(select(candidatures)).all() == []
    assert "introuvable" in api.de_type("answer_callback")[0][2]


@pytest.mark.parametrize("donnee", ["zzz", "p:abc", "noop", ""])
def test_donnee_mal_formee_recoit_une_reponse_neutre(session, donnee):
    oid = _offre(session)
    api = FauxAPI([_bouton(10, donnee)])
    _lancer(session, api)
    assert _statut(session, oid) is None
    assert len(api.de_type("answer_callback")) == 1


def test_brouillon_annonce_l_etape_c5(session):
    oid = _offre(session)
    api = FauxAPI([_bouton(10, f"b:{oid}")])
    _lancer(session, api)
    assert "C5" in api.de_type("answer_callback")[0][2]
    assert _statut(session, oid) is None


@pytest.mark.parametrize(("action", "statut"), [("r", Statut.INTERESSANTE), ("x", Statut.IGNOREE)])
def test_rappel_et_ignorer(session, action, statut):
    oid = _offre(session)
    api = FauxAPI([_bouton(10, f"{action}:{oid}")])
    _lancer(session, api)
    assert _statut(session, oid) is statut
    assert len(api.de_type("answer_callback")) == 1


def test_chat_etranger_message_aucun_appel_et_base_inchangee(session):
    api = FauxAPI([_message(10, "/pause", chat="999")])
    _lancer(session, api)
    assert api.de_type("send_message") == [] and api.de_type("answer_callback") == []
    assert repo.get_param(session, "pause") is None


def test_chat_etranger_bouton_aucun_appel_et_base_inchangee(session):
    oid = _offre(session)
    api = FauxAPI([_bouton(10, f"x:{oid}", chat="999", auteur="999")])
    _lancer(session, api)
    assert _statut(session, oid) is None
    assert api.de_type("answer_callback") == [] and api.de_type("edit_keyboard") == []


def test_bouton_d_un_autre_chat_meme_avec_le_bon_auteur_est_ignore(session):
    oid = _offre(session)
    api = FauxAPI([_bouton(10, f"x:{oid}", chat="999", auteur=CHAT)])
    _lancer(session, api)
    assert _statut(session, oid) is None and api.de_type("answer_callback") == []


def test_bouton_d_un_autre_compte_dans_le_bon_chat_est_ignore(session):
    oid = _offre(session)
    api = FauxAPI([_bouton(10, f"x:{oid}", chat=CHAT, auteur="999")])
    _lancer(session, api)
    assert _statut(session, oid) is None and api.de_type("answer_callback") == []


def test_update_etrangere_fait_quand_meme_avancer_l_offset(session):
    api = FauxAPI([_message(10, "x", chat="999")], [])
    _lancer(session, api, tours=2)
    assert api.de_type("get_updates")[1] == ("get_updates", 11, 50)


def test_update_dupliquee_n_agit_qu_une_fois(session):
    oid = _offre(session)
    api = FauxAPI([_bouton(10, f"p:{oid}"), _bouton(10, f"p:{oid}")], [_bouton(10, f"p:{oid}")])
    _lancer(session, api, tours=2)
    assert len(api.de_type("answer_callback")) == 1


def test_update_plus_ancienne_ignoree(session):
    repo.set_param(session, "dernier_update_id", "50")
    session.commit()
    api = FauxAPI([_message(49, "/pause")])
    _lancer(session, api)
    assert repo.get_param(session, "pause") is None
    assert repo.get_param(session, "dernier_update_id") == "50"


def test_redemarrage_reprend_a_l_update_suivante(session):
    repo.set_param(session, "dernier_update_id", "41")
    session.commit()
    api = FauxAPI([])
    _lancer(session, api)
    assert api.de_type("get_updates") == [("get_updates", 42, 50)]


def test_dernier_update_id_enregistre_apres_chaque_update(session):
    api = FauxAPI([_message(10, "/stats"), _message(11, "/stats")])
    _lancer(session, api)
    assert repo.get_param(session, "dernier_update_id") == "11"


def test_erreur_reseau_attend_puis_continue(session):
    oid = _offre(session)
    api = FauxAPI(TelegramError("Telegram getUpdates : ConnectError"), [_bouton(10, f"x:{oid}")])
    pauses = _lancer(session, api, tours=2)
    assert pauses == [5]
    assert _statut(session, oid) is Statut.IGNOREE


def test_update_defectueuse_ne_bloque_pas_les_suivantes(session):
    oid = _offre(session)
    api = FauxAPI([_message(10, "/stats"), _bouton(11, f"x:{oid}")], echec_envoi=TelegramError("boom"))
    _lancer(session, api)
    assert _statut(session, oid) is Statut.IGNOREE
    assert repo.get_param(session, "dernier_update_id") == "11"


def test_charge_inattendue_ignoree_sans_erreur(session):
    api = FauxAPI([{"update_id": 10, "edited_message": {}}, {"update_id": 11}, _message(12, "/stats")])
    _lancer(session, api)
    assert len(api.de_type("send_message")) == 1
    assert repo.get_param(session, "dernier_update_id") == "12"


def test_commande_envoyee_avec_son_clavier(session):
    oid = _offre(session)
    repo.marquer(session, oid, Statut.INTERESSANTE, NOW)
    session.commit()
    api = FauxAPI([_message(10, "/candidatures")])
    _lancer(session, api)
    ((_, texte, clavier),) = api.de_type("send_message")
    assert "Dev 1" in texte and clavier is None
    api = FauxAPI([_message(11, "/pause")])
    _lancer(session, api)
    assert repo.get_param(session, "pause") == "1"
