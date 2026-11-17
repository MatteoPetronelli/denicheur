from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from denicheur.config import load_config
from denicheur.db import repo
from denicheur.db.base import make_engine, migrer
from denicheur.db.tables import brouillons, candidatures
from denicheur.models import Offre, Piste, ScoreLLM, Statut
from denicheur.redaction.documents import ErreurDocuments
from denicheur.redaction.gmail_drafts import ErreurGmail
from denicheur.redaction.prompts import ProfilManquant
from denicheur.redaction.service import RedactionInvalide
from denicheur.scoring.llm import OllamaIndisponible
from denicheur.telegram.api import TelegramError
from denicheur.telegram.bot import BotDeps, boucle
from denicheur.telegram.keyboard import clavier_brouillon, clavier_depose, clavier_envoyee

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

    def send_document(self, nom, octets, type_mime):
        self.appels.append(("send_document", nom, octets, type_mime))
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


def _lancer(session, api, tours=1, **options):
    restants = iter([True] * tours)
    pauses: list[float] = []
    deps = BotDeps(api, session, CONFIG, CHAT, lambda: NOW, **options)
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


# --- brouillons : b, g, l ---
PROFIL_LIGNE = "Éléments du profil utilisés : RiftMind"
TEXTE = f"Madame, Monsieur,\n\nCorps <b>piégé</b> & accentué.\n\n{PROFIL_LIGNE}"


class FauxRedacteur:
    def __init__(self, api, texte=TEXTE, erreur=None):
        self.api, self.texte, self.erreur = api, texte, erreur
        self.demandes: list[tuple[str, str]] = []

    def rediger(self, offre, score, type_):
        self.api.appels.append(("rediger", type_))
        self.demandes.append((offre.titre, type_))
        if self.erreur:
            raise self.erreur
        return self.texte


class FauxDepot:
    def __init__(self, erreur=None):
        self.erreur = erreur
        self.depots: list[tuple[str, str]] = []
        self.pieces: list = []

    def __call__(self, sujet, corps, pieces=()):
        if self.erreur:
            raise self.erreur
        self.depots.append((sujet, corps))
        self.pieces.append(list(pieces))


def _notee(session, n=1):
    oid = _offre(session, n)
    score = ScoreLLM(
        score=80, type="alternance", points_forts=[], points_faibles=[], alerte=None,
        projet_a_citer="RiftMind", resume="r",
    )  # fmt: skip
    repo.inserer_score(session, oid, score, modele="m", prompt_tokens=1, output_tokens=1, duree_s=1, now=NOW)
    session.commit()
    return oid


def _brouillons(session):
    return session.execute(select(brouillons)).mappings().all()


def _texte_du_message(api):
    ((_, texte, clavier),) = api.de_type("send_message")
    return texte, clavier


def test_brouillon_repond_attente_puis_genere_enregistre_et_envoie_avec_le_bouton_gmail(session):
    oid = _notee(session)
    api = FauxAPI([_bouton(10, f"b:{oid}")])
    redacteur = FauxRedacteur(api)
    _lancer(session, api, redacteur=redacteur)
    ordre = [a[0] for a in api.appels if a[0] in ("answer_callback", "rediger", "send_message")]
    assert ordre == ["answer_callback", "rediger", "send_message"]
    assert api.de_type("answer_callback")[0][2] == "⏳ Rédaction…"
    assert redacteur.demandes == [("Dev 1", "email")]
    (ligne,) = _brouillons(session)
    assert ligne["type"] == "email" and ligne["contenu"] == TEXTE and ligne["gmail_draft"] is False
    texte, clavier = _texte_du_message(api)
    assert clavier == clavier_brouillon(ligne["id"])
    assert "Corps &lt;b&gt;piégé&lt;/b&gt; &amp; accentué." in texte and "<b>piégé</b>" not in texte
    assert PROFIL_LIGNE in texte
    assert repo.statut_de(session, oid) is Statut.INTERESSANTE


def test_brouillon_sur_offre_ignoree_refuse_sans_appel_au_modele(session):
    oid = _notee(session)
    repo.marquer(session, oid, Statut.IGNOREE, NOW)
    session.commit()
    api = FauxAPI([_bouton(10, f"b:{oid}")])
    redacteur = FauxRedacteur(api)
    _lancer(session, api, redacteur=redacteur)
    assert redacteur.demandes == [] and "Impossible" in api.de_type("answer_callback")[0][2]
    assert _brouillons(session) == [] and api.de_type("send_message") == []


def test_brouillon_offre_inconnue(session):
    api = FauxAPI([_bouton(10, "b:999")])
    redacteur = FauxRedacteur(api)
    _lancer(session, api, redacteur=redacteur)
    assert redacteur.demandes == [] and "introuvable" in api.de_type("answer_callback")[0][2]


def test_brouillon_offre_non_notee(session):
    oid = _offre(session)
    api = FauxAPI([_bouton(10, f"b:{oid}")])
    redacteur = FauxRedacteur(api)
    _lancer(session, api, redacteur=redacteur)
    assert redacteur.demandes == [] and "non notée" in api.de_type("answer_callback")[0][2]
    assert _statut(session, oid) is None


def test_brouillon_sans_redacteur_configure(session):
    oid = _notee(session)
    api = FauxAPI([_bouton(10, f"b:{oid}")])
    _lancer(session, api)
    assert "non configurée" in api.de_type("answer_callback")[0][2]
    assert _brouillons(session) == [] and _statut(session, oid) is None


@pytest.mark.parametrize(
    ("erreur", "fragment"),
    [
        (OllamaIndisponible("http://localhost:11434 refusé"), "Ollama"),
        (RedactionInvalide("ReadTimeout"), "dépassé le délai"),
        (ProfilManquant("Fichier de profil introuvable : profil.md"), "profil.md"),
    ],
)
def test_echec_de_redaction_message_francais_sans_detail_et_boucle_intacte(session, erreur, fragment):
    oid, autre = _notee(session, 1), _notee(session, 2)
    api = FauxAPI([_bouton(10, f"b:{oid}"), _bouton(11, f"x:{autre}")])
    _lancer(session, api, redacteur=FauxRedacteur(api, erreur=erreur))
    ((_, texte, clavier),) = api.de_type("send_message")
    assert fragment in texte and "localhost" not in texte and "ReadTimeout" not in texte and clavier is None
    assert _brouillons(session) == [] and _statut(session, oid) is None
    assert _statut(session, autre) is Statut.IGNOREE  # la mise à jour suivante est traitée
    assert repo.get_param(session, "dernier_update_id") == "11"


def test_brouillon_d_un_chat_etranger_ne_declenche_rien(session):
    oid = _notee(session)
    api = FauxAPI([_bouton(10, f"b:{oid}", chat="999", auteur="999")])
    redacteur = FauxRedacteur(api)
    _lancer(session, api, redacteur=redacteur)
    assert redacteur.demandes == [] and api.de_type("answer_callback") == []


def _avec_brouillon(session, n=1):
    oid = _notee(session, n)
    bid = repo.enregistrer_brouillon(session, oid, "email", TEXTE, NOW)
    session.commit()
    return oid, bid


def test_depot_gmail_une_fois_sans_ligne_de_profil_puis_clavier_inerte(session):
    oid, bid = _avec_brouillon(session)
    api = FauxAPI([_bouton(10, f"g:{bid}", message_id=55)])
    depot = FauxDepot()
    _lancer(session, api, deposer=depot)
    assert depot.depots == [("Candidature : Dev 1", "Madame, Monsieur,\n\nCorps <b>piégé</b> & accentué.")]
    assert api.de_type("answer_callback")[0][2] == "📥 Brouillon Gmail créé"
    assert api.de_type("edit_keyboard") == [("edit_keyboard", 55, clavier_depose())]
    assert repo.lire_brouillon(session, bid).depose is True


def test_depot_gmail_deux_fois_un_seul_depot(session):
    _, bid = _avec_brouillon(session)
    api = FauxAPI([_bouton(10, f"g:{bid}"), _bouton(11, f"g:{bid}")])
    depot = FauxDepot()
    _lancer(session, api, deposer=depot)
    assert len(depot.depots) == 1
    assert "Déjà" in api.de_type("answer_callback")[1][2]


def test_depot_gmail_en_echec_laisse_le_brouillon_non_depose_et_reessayable(session):
    _, bid = _avec_brouillon(session)
    api = FauxAPI([_bouton(10, f"g:{bid}")])
    _lancer(session, api, deposer=FauxDepot(ErreurGmail("Connexion IMAP refusée")))
    assert "Échec" in api.de_type("answer_callback")[0][2]
    assert repo.lire_brouillon(session, bid).depose is False and api.de_type("edit_keyboard") == []
    api = FauxAPI([_bouton(11, f"g:{bid}")])
    depot = FauxDepot()
    _lancer(session, api, deposer=depot)
    assert len(depot.depots) == 1 and repo.lire_brouillon(session, bid).depose is True


def test_depot_gmail_brouillon_inconnu(session):
    api = FauxAPI([_bouton(10, "g:999")])
    depot = FauxDepot()
    _lancer(session, api, deposer=depot)
    assert depot.depots == [] and "introuvable" in api.de_type("answer_callback")[0][2]


def test_depot_gmail_non_configure(session):
    _, bid = _avec_brouillon(session)
    api = FauxAPI([_bouton(10, f"g:{bid}")])
    _lancer(session, api)
    assert "Gmail non configuré" in api.de_type("answer_callback")[0][2]
    assert repo.lire_brouillon(session, bid).depose is False


def test_depot_gmail_d_un_autre_compte_est_ignore(session):
    _, bid = _avec_brouillon(session)
    api = FauxAPI([_bouton(10, f"g:{bid}", chat=CHAT, auteur="999")])
    depot = FauxDepot()
    _lancer(session, api, deposer=depot)
    assert depot.depots == [] and api.de_type("answer_callback") == []


def _envoyee(session, n=1):
    oid = _notee(session, n)
    repo.marquer(session, oid, Statut.CANDIDATURE_ENVOYEE, NOW)
    session.commit()
    return oid


def test_relance_genere_enregistre_marque_relancee_et_propose_le_depot(session):
    oid = _envoyee(session)
    api = FauxAPI([_bouton(10, f"l:{oid}")])
    redacteur = FauxRedacteur(api)
    _lancer(session, api, redacteur=redacteur)
    assert redacteur.demandes == [("Dev 1", "relance")]
    (ligne,) = _brouillons(session)
    assert ligne["type"] == "relance"
    assert repo.statut_de(session, oid) is Statut.RELANCEE
    _, clavier = _texte_du_message(api)
    assert clavier == clavier_brouillon(ligne["id"])


def test_seconde_relance_refusee_sans_nouvel_appel_au_modele(session):
    oid = _envoyee(session)
    api = FauxAPI([_bouton(10, f"l:{oid}"), _bouton(11, f"l:{oid}")])
    redacteur = FauxRedacteur(api)
    _lancer(session, api, redacteur=redacteur)
    assert len(redacteur.demandes) == 1 and len(_brouillons(session)) == 1
    assert "Une seule relance" in api.de_type("answer_callback")[-1][2]
    assert len(api.de_type("send_message")) == 1


@pytest.mark.parametrize("prealable", [None, Statut.INTERESSANTE, Statut.IGNOREE])
def test_relance_impossible_hors_candidature_envoyee(session, prealable):
    oid = _notee(session)
    if prealable:
        repo.marquer(session, oid, prealable, NOW)
        session.commit()
    api = FauxAPI([_bouton(10, f"l:{oid}")])
    redacteur = FauxRedacteur(api)
    _lancer(session, api, redacteur=redacteur)
    assert redacteur.demandes == [] and "Impossible" in api.de_type("answer_callback")[0][2]
    assert _brouillons(session) == [] and _statut(session, oid) is prealable


def test_relance_offre_inconnue(session):
    api = FauxAPI([_bouton(10, "l:999")])
    redacteur = FauxRedacteur(api)
    _lancer(session, api, redacteur=redacteur)
    assert redacteur.demandes == [] and "introuvable" in api.de_type("answer_callback")[0][2]


def test_relance_en_echec_ne_marque_pas_relancee(session):
    oid = _envoyee(session)
    api = FauxAPI([_bouton(10, f"l:{oid}")])
    _lancer(session, api, redacteur=FauxRedacteur(api, erreur=RedactionInvalide("x")))
    assert repo.statut_de(session, oid) is Statut.CANDIDATURE_ENVOYEE and _brouillons(session) == []


def test_la_duree_de_redaction_est_journalisee(session, caplog):
    oid = _notee(session)
    api = FauxAPI([_bouton(10, f"b:{oid}")])
    with caplog.at_level("INFO", logger="denicheur.telegram.bot"):
        _lancer(session, api, redacteur=FauxRedacteur(api))
    (message,) = [r.getMessage() for r in caplog.records if r.name == "denicheur.telegram.bot"]
    assert message.startswith("rédaction email offre") and message.endswith(" s")
    assert "Madame" not in message and "localhost" not in message


# --- lettre PDF : d, et dépôt avec pièce jointe ---
@pytest.fixture
def lettres(tmp_path):
    """(options du bot, dossier des lettres) : identité locale factice, dossier temporaire."""
    identite = tmp_path / "identite.md"
    identite.write_text(
        "nom: Jeanne Exemple\nadresse: 1 rue des Tests\nville: 75001 Paris\n"
        "telephone: 01 02 03 04 05\nemail: jeanne@exemple.test\n",
        encoding="utf-8",
    )
    dossier = tmp_path / "lettres"
    dossier.mkdir()
    return {"dossier_lettres": dossier, "chemin_identite": identite}, dossier


def _noms(dossier):
    return sorted(p.name for p in dossier.iterdir())


def test_lettre_ecrit_les_deux_fichiers_les_envoie_puis_propose_le_depot(session, lettres):
    options, dossier = lettres
    oid = _notee(session)
    api = FauxAPI([_bouton(10, f"d:{oid}")])
    redacteur = FauxRedacteur(api)
    _lancer(session, api, redacteur=redacteur, **options)
    assert redacteur.demandes == [("Dev 1", "lettre")]
    assert _noms(dossier) == ["Lettre de motivation ACME.docx", "Lettre de motivation ACME.pdf"]
    ordre = [a[0] for a in api.appels if a[0] in ("send_message", "send_document")]
    assert ordre == ["send_message", "send_document", "send_document", "send_message"]
    texte, doc1, doc2, accompagnement = (
        [a for a in api.appels if a[0] == "send_message"][0],
        *api.de_type("send_document"),
        [a for a in api.appels if a[0] == "send_message"][1],
    )
    assert PROFIL_LIGNE in texte[1]  # le texte relu garde la ligne de vérification
    assert (doc1[1], doc1[3]) == ("Lettre de motivation ACME.pdf", "application/pdf") and doc1[2][
        :4
    ] == b"%PDF"
    assert doc2[1] == "Lettre de motivation ACME.docx" and doc2[2][:2] == b"PK"
    (ligne,) = _brouillons(session)
    assert ligne["type"] == "lettre" and accompagnement[2] == clavier_brouillon(ligne["id"])
    assert (
        "Dev 1" in accompagnement[1] and "ACME" in accompagnement[1] and "Jeanne Exemple" in accompagnement[1]
    )
    assert repo.statut_de(session, oid) is Statut.INTERESSANTE


def test_lettre_sur_offre_ignoree_aucun_appel_ni_fichier(session, lettres):
    options, dossier = lettres
    oid = _notee(session)
    repo.marquer(session, oid, Statut.IGNOREE, NOW)
    session.commit()
    api = FauxAPI([_bouton(10, f"d:{oid}")])
    redacteur = FauxRedacteur(api)
    _lancer(session, api, redacteur=redacteur, **options)
    assert (
        redacteur.demandes == []
        and _noms(dossier) == []
        and "Impossible" in api.de_type("answer_callback")[0][2]
    )


def test_lettre_identite_absente_refus_avant_l_appel_au_modele(session, lettres):
    options, dossier = lettres
    options["chemin_identite"].unlink()
    oid = _notee(session)
    api = FauxAPI([_bouton(10, f"d:{oid}")])
    redacteur = FauxRedacteur(api)
    _lancer(session, api, redacteur=redacteur, **options)
    assert redacteur.demandes == [] and _noms(dossier) == [] and _brouillons(session) == []
    assert "identité" in api.de_type("answer_callback")[0][2]


def test_lettre_dossier_absent_refus_avant_l_appel_au_modele(session, lettres, tmp_path):
    options, _ = lettres
    options["dossier_lettres"] = tmp_path / "inexistant"
    oid = _notee(session)
    api = FauxAPI([_bouton(10, f"d:{oid}")])
    redacteur = FauxRedacteur(api)
    _lancer(session, api, redacteur=redacteur, **options)
    assert redacteur.demandes == [] and "Dossier des lettres" in api.de_type("answer_callback")[0][2]
    assert str(tmp_path) not in api.de_type("answer_callback")[0][2]


def test_lettre_dossier_non_configure(session):
    oid = _notee(session)
    api = FauxAPI([_bouton(10, f"d:{oid}")])
    redacteur = FauxRedacteur(api)
    _lancer(session, api, redacteur=redacteur)
    assert redacteur.demandes == [] and "non configuré" in api.de_type("answer_callback")[0][2]


def test_lettre_echec_d_ecriture_message_sans_chemin_et_aucun_brouillon(session, lettres, monkeypatch):
    options, dossier = lettres

    def echec(*a, **k):
        raise ErreurDocuments("Écriture impossible dans le dossier des lettres")

    monkeypatch.setattr("denicheur.telegram.bot.ecrire_lettre", echec)
    oid = _notee(session)
    autre = _notee(session, 2)
    api = FauxAPI([_bouton(10, f"d:{oid}"), _bouton(11, f"x:{autre}")])
    _lancer(session, api, redacteur=FauxRedacteur(api), **options)
    ((_, texte, _clavier),) = api.de_type("send_message")
    assert "lettre" in texte and str(dossier) not in texte
    assert _brouillons(session) == [] and api.de_type("send_document") == []
    assert _statut(session, autre) is Statut.IGNOREE and _statut(session, oid) is None


def test_lettre_d_un_chat_etranger_ne_declenche_rien(session, lettres):
    options, dossier = lettres
    oid = _notee(session)
    api = FauxAPI([_bouton(10, f"d:{oid}", chat="999", auteur="999")])
    redacteur = FauxRedacteur(api)
    _lancer(session, api, redacteur=redacteur, **options)
    assert redacteur.demandes == [] and _noms(dossier) == []
    assert api.de_type("send_message") == [] and api.de_type("send_document") == []


def _avec_lettre(session):
    oid = _notee(session)
    bid = repo.enregistrer_brouillon(session, oid, "lettre", TEXTE, NOW)
    session.commit()
    return oid, bid


def test_depot_gmail_d_une_lettre_joint_le_pdf_sans_rien_ecrire_dans_le_dossier(session, lettres):
    options, dossier = lettres
    _, bid = _avec_lettre(session)
    api = FauxAPI([_bouton(10, f"g:{bid}")])
    depot = FauxDepot()
    _lancer(session, api, deposer=depot, **options)
    ((sujet, corps),) = depot.depots
    assert sujet == "Candidature : Dev 1"
    assert (
        corps.startswith("Madame, Monsieur,")
        and "ci-joint" in corps
        and corps.rstrip().endswith("Jeanne Exemple")
    )
    assert PROFIL_LIGNE not in corps
    ((piece,),) = depot.pieces
    assert piece.nom == "Lettre de motivation ACME.pdf" and piece.type_mime == "application/pdf"
    assert piece.octets[:4] == b"%PDF"
    assert _noms(dossier) == []
    assert repo.lire_brouillon(session, bid).depose is True


def test_depot_gmail_d_un_brouillon_email_sans_piece_jointe(session, lettres):
    options, _ = lettres
    _, bid = _avec_brouillon(session)
    api = FauxAPI([_bouton(10, f"g:{bid}")])
    depot = FauxDepot()
    _lancer(session, api, deposer=depot, **options)
    assert depot.pieces == [[]]


def test_depot_gmail_d_une_lettre_identite_absente_aucun_depot(session, lettres):
    options, _ = lettres
    options["chemin_identite"].unlink()
    _, bid = _avec_lettre(session)
    api = FauxAPI([_bouton(10, f"g:{bid}")])
    depot = FauxDepot()
    _lancer(session, api, deposer=depot, **options)
    assert depot.depots == [] and "identité" in api.de_type("answer_callback")[0][2]
    assert repo.lire_brouillon(session, bid).depose is False


def test_echec_de_redaction_est_journalise_sans_detail_interne(session, caplog):
    oid = _notee(session)
    api = FauxAPI([_bouton(10, f"b:{oid}")])
    with caplog.at_level("WARNING", logger="denicheur.telegram.bot"):
        _lancer(session, api, redacteur=FauxRedacteur(api, erreur=RedactionInvalide("ReadTimeout")))
    (message,) = [r.getMessage() for r in caplog.records if r.name == "denicheur.telegram.bot"]
    assert "ReadTimeout" in message and f"offre {oid}" in message and " s" in message
    assert "localhost" not in message and "http" not in message


def _liens(tmp_path):
    chemin = tmp_path / "liens.md"
    chemin.write_text(
        "github: https://github.com/exemple/\nprojet RiftMind: https://github.com/exemple/riftmind\n",
        encoding="utf-8",
    )
    return chemin


def _texte_pdf(octets):
    import io

    from pypdf import PdfReader

    return "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(octets)).pages)


def test_lettre_ajoute_le_lien_du_projet_cite_dans_les_fichiers_envoyes(session, lettres, tmp_path):
    options, dossier = lettres
    options["chemin_liens"] = _liens(tmp_path)
    oid = _notee(session)
    texte = f"Madame, Monsieur,\n\nJ'ai créé RiftMind en Rust.\n\nCordialement.\n\n{PROFIL_LIGNE}"
    api = FauxAPI([_bouton(10, f"d:{oid}")])
    _lancer(session, api, redacteur=FauxRedacteur(api, texte=texte), **options)
    pdf = api.de_type("send_document")[0][2]
    assert "https://github.com/exemple/riftmind" in _texte_pdf(
        pdf
    ) and "GitHub : https://github.com/exemple/" in _texte_pdf(pdf)
    assert pdf == (dossier / "Lettre de motivation ACME.pdf").read_bytes()


def test_depot_gmail_d_une_lettre_joint_un_pdf_avec_les_liens(session, lettres, tmp_path):
    options, _ = lettres
    options["chemin_liens"] = _liens(tmp_path)
    oid = _notee(session)
    texte = f"Madame, Monsieur,\n\nJ'ai créé RiftMind en Rust.\n\n{PROFIL_LIGNE}"
    bid = repo.enregistrer_brouillon(session, oid, "lettre", texte, NOW)
    session.commit()
    api = FauxAPI([_bouton(10, f"g:{bid}")])
    depot = FauxDepot()
    _lancer(session, api, deposer=depot, **options)
    assert "https://github.com/exemple/riftmind" in _texte_pdf(depot.pieces[0][0].octets)
