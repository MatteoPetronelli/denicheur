import re
from pathlib import Path

import httpx
import pytest

from denicheur.config import load_config
from denicheur.models import Offre, Piste, ScoreLLM
from denicheur.redaction import prompts
from denicheur.redaction.prompts import ProfilManquant, message_systeme, message_utilisateur
from denicheur.redaction.service import Redacteur, RedactionInvalide
from denicheur.scoring.llm import OllamaIndisponible

RACINE = Path(__file__).parent.parent
cfg = load_config(RACINE / "config" / "recherches.yaml")
TEL = re.compile(r"\b0\d([\s.-]?\d{2}){4}\b")
EMAIL = re.compile(r"\S+@\S+")
LIGNE = "Éléments du profil utilisés"


def _offre(**kw):
    base = {
        "source": "t", "source_id": "1", "url": "u1", "titre": "Développeur Python", "entreprise": "ACME",
        "commune": "Paris", "lat": 48.88, "lon": 2.0775, "piste": Piste.ALTERNANCE, "duree_mois": 12,
        "debut": None, "niveau_diplome": "6", "description": "Une équipe produit.", "publiee_le": None,
        "expire_le": None, "distance_km": 4.2,
    }  # fmt: skip
    return Offre(**{**base, **kw})


SCORE = ScoreLLM(
    score=80, type="alternance", points_forts=["a"], points_faibles=["b"], alerte=None,
    projet_a_citer="RiftMind", resume="r",
)  # fmt: skip


def _mots(n: int, tag: str = "mot") -> str:
    return " ".join(f"{tag}{i}" for i in range(n))


def _texte(n: int, ligne: str | None = f"{LIGNE} : RiftMind, Python", tag: str = "mot") -> str:
    return _mots(n, tag) + (f"\n{ligne}" if ligne else "")


class Ollama:
    """Faux serveur : rejoue des réponses de /api/chat et garde les requêtes."""

    def __init__(self, *reponses):
        self.reponses = list(reponses)
        self.requetes: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requetes.append(request)
        r = self.reponses.pop(0)
        if isinstance(r, Exception):
            raise r
        if isinstance(r, httpx.Response):
            return r
        return httpx.Response(200, json={"message": {"content": r}})

    def corps(self, i=0):
        import json

        return json.loads(self.requetes[i].content)


def _redacteur(ollama, profil, horloge=None):
    http = httpx.Client(transport=httpx.MockTransport(ollama))
    args = {"horloge": horloge} if horloge else {}
    return Redacteur(cfg.llm, http, dossier=profil, **args)


def _horloge(*valeurs):
    it = iter(valeurs)
    return lambda: next(it)


# --- prompts ---
def test_systeme_compose_des_trois_fichiers_et_stable(profil):
    s = message_systeme(profil)
    assert s == message_systeme(profil)
    assert s.index("REGLES-SENTINELLE") < s.index("MODELE-SENTINELLE") < s.index("PROFIL-SENTINELLE")


def test_systeme_sans_cv_local_ni_contact(profil):
    s = message_systeme(profil)
    assert "CV-SECRET" not in s and not TEL.search(s) and not EMAIL.search(s)


def test_systeme_reel_sans_donnee_personnelle():
    s = message_systeme()
    assert not TEL.search(s) and not EMAIL.search(s)
    assert "RiftMind" in s and "Exa informatique" in s


@pytest.mark.parametrize("manquant", ["regles_ecriture.md", "lettre_modele.md", "profil.md"])
def test_fichier_de_profil_absent_leve_une_erreur_francaise_sans_appel(profil, manquant):
    (profil / manquant).unlink()
    ollama = Ollama("x")
    with pytest.raises(ProfilManquant, match=manquant):
        _redacteur(ollama, profil).rediger(_offre(), SCORE, "email")
    assert ollama.requetes == []


def test_message_utilisateur_porte_offre_projet_et_disponibilite():
    m = message_utilisateur(_offre(entreprise="Globex"), SCORE, "email")
    assert "Globex" in m and "RiftMind" in m and "Développeur Python" in m
    assert "une semaine d'école pour deux semaines en entreprise" in m and "dès que possible" in m
    assert "aucun trou à compléter" in m and "vise 150 mots" in m


def test_disponibilite_du_stage():
    m = message_utilisateur(_offre(piste=Piste.STAGE), SCORE, "email")
    assert "janvier 2027" in m and "5 à 6 mois" in m


def test_contacts_effaces_de_la_description():
    d = "Écrire à jean.dupont@exemple.fr ou appeler le 01 23 45 67 89."
    m = message_utilisateur(_offre(description=d), SCORE, "email")
    assert not EMAIL.search(m) and not TEL.search(m)


def test_type_decrit_la_plage_de_mots():
    assert "120 à 180" in message_utilisateur(_offre(), SCORE, "email")
    assert "250 à 300" in message_utilisateur(_offre(), SCORE, "lettre")


def test_prompts_exposent_les_types():
    assert set(prompts.TYPES) == {"email", "lettre", "relance", "spontanee"}


# --- appel au modèle ---
def test_requete_utilise_exactement_la_config_ecriture(profil):
    ollama = Ollama(_texte(150))
    _redacteur(ollama, profil).rediger(_offre(), SCORE, "email")
    corps = ollama.corps()
    c = cfg.llm.ecriture
    assert corps["model"] == c.modele and corps["stream"] is False
    assert corps["options"] == {"temperature": c.temperature, "num_ctx": c.num_ctx}
    assert ollama.requetes[0].extensions["timeout"]["read"] == c.timeout_s
    assert corps["messages"][0] == {"role": "system", "content": message_systeme(profil)}


def test_type_inconnu_refuse_avant_tout_appel(profil):
    ollama = Ollama("x")
    with pytest.raises(ValueError, match="bidule"):
        _redacteur(ollama, profil).rediger(_offre(), SCORE, "bidule")
    assert ollama.requetes == []


def test_ollama_arrete(profil):
    ollama = Ollama(httpx.ConnectError("refusé"))
    with pytest.raises(OllamaIndisponible):
        _redacteur(ollama, profil).rediger(_offre(), SCORE, "email")


@pytest.mark.parametrize(
    "reponse",
    [httpx.Response(500), httpx.ReadTimeout("lent"), httpx.Response(200, json={"message": {"content": ""}}),
     httpx.Response(200, json={"oups": 1}), httpx.Response(200, text="pas du json")],
)  # fmt: skip
def test_reponse_inutilisable_sans_detail_interne(profil, reponse):
    ollama = Ollama(reponse)
    with pytest.raises(RedactionInvalide) as e:
        _redacteur(ollama, profil).rediger(_offre(), SCORE, "email")
    assert "localhost" not in str(e.value) and "http" not in str(e.value)


# --- longueur ---
def test_dans_la_plage_un_seul_appel_sans_note(profil):
    ollama = Ollama(_texte(150))
    texte = _redacteur(ollama, profil).rediger(_offre(), SCORE, "email")
    assert len(ollama.requetes) == 1 and "⚠️" not in texte


def test_un_second_essai_dans_la_plage_est_livre_sans_note(profil):
    ollama = Ollama(_texte(90, tag="a"), _texte(140, tag="b"))
    texte = _redacteur(ollama, profil).rediger(_offre(), SCORE, "email")
    assert len(ollama.requetes) == 2 and "⚠️" not in texte and "b139" in texte and "a0 " not in texte


def test_deux_echecs_livre_le_plus_proche_avec_note_sans_troisieme_appel(profil):
    ollama = Ollama(_texte(60, tag="a"), _texte(110, tag="b"), _texte(150, tag="c"))
    texte = _redacteur(ollama, profil).rediger(_offre(), SCORE, "email")
    assert len(ollama.requetes) == 2
    assert "b109" in texte and "a59" not in texte
    assert "⚠" not in texte and texte.splitlines()[-1].startswith(LIGNE)


def test_le_meilleur_est_aussi_le_premier(profil):
    ollama = Ollama(_texte(115, tag="a"), _texte(40, tag="b"))
    texte = _redacteur(ollama, profil).rediger(_offre(), SCORE, "email")
    assert "a114" in texte and "b39" not in texte and "⚠" not in texte


def test_premier_essai_lent_pas_de_second_appel(profil):
    ollama = Ollama(_texte(90), _texte(140))
    texte = _redacteur(ollama, profil, _horloge(0.0, 46.0)).rediger(_offre(), SCORE, "email")
    assert len(ollama.requetes) == 1 and "⚠" not in texte


def test_premier_essai_rapide_autorise_le_second(profil):
    ollama = Ollama(_texte(90), _texte(140))
    _redacteur(ollama, profil, _horloge(0.0, 44.0, 44.0, 50.0)).rediger(_offre(), SCORE, "email")
    assert len(ollama.requetes) == 2


def test_le_second_essai_signale_la_longueur_du_premier(profil):
    ollama = Ollama(_texte(90), _texte(140))
    _redacteur(ollama, profil).rediger(_offre(), SCORE, "email")
    dernier = ollama.corps(1)["messages"][-1]["content"]
    assert "90 mots" in dernier and "120 à 180" in dernier


def test_la_ligne_de_profil_n_entre_pas_dans_le_decompte(profil):
    long_profil = f"{LIGNE} : " + ", ".join(f"element{i}" for i in range(80))
    ollama = Ollama(_texte(120, long_profil))
    texte = _redacteur(ollama, profil).rediger(_offre(), SCORE, "email")
    assert len(ollama.requetes) == 1 and "⚠️" not in texte


@pytest.mark.parametrize("type_", ["email", "relance", "spontanee"])
def test_relance_et_spontanee_suivent_la_plage_de_l_email(profil, type_):
    ollama = Ollama(_texte(150))
    texte = _redacteur(ollama, profil).rediger(_offre(), SCORE, type_)
    assert len(ollama.requetes) == 1 and "⚠️" not in texte


def test_lettre_demande_250_a_300_mots(profil):
    ollama = Ollama(_texte(200), _texte(270))
    texte = _redacteur(ollama, profil).rediger(_offre(), SCORE, "lettre")
    assert len(ollama.requetes) == 2 and "⚠️" not in texte


# --- ligne de profil et marqueur ---
def test_ligne_de_profil_presente_reste_la_derniere(profil):
    texte = _redacteur(Ollama(_texte(150)), profil).rediger(_offre(), SCORE, "email")
    assert texte.splitlines()[-1] == f"{LIGNE} : RiftMind, Python"


def test_ligne_de_profil_absente_est_ajoutee_en_dernier(profil):
    texte = _redacteur(Ollama(_texte(150, None)), profil).rediger(_offre(), SCORE, "email")
    derniere = texte.splitlines()[-1]
    assert derniere.startswith(LIGNE) and "impossible" in derniere
    assert texte.count(LIGNE) == 1


def test_ce_qui_suit_la_ligne_de_profil_est_ecarte(profil):
    brut = _texte(150) + "\nN'hésitez pas à me demander des changements."
    texte = _redacteur(Ollama(brut), profil).rediger(_offre(), SCORE, "email")
    assert texte.splitlines()[-1].startswith(LIGNE) and "changements" not in texte


def test_hors_plage_aucune_note_dans_le_texte_mais_une_ligne_de_journal(profil, caplog):
    with caplog.at_level("INFO", logger="denicheur.redaction.service"):
        texte = _redacteur(Ollama(_texte(60), _texte(70)), profil).rediger(_offre(), SCORE, "email")
    assert "⚠" not in texte and "hors plage" not in texte
    assert texte.splitlines()[-1].startswith(LIGNE)
    (message,) = [r.getMessage() for r in caplog.records if r.name == "denicheur.redaction.service"]
    assert "email hors plage" in message and "70 mots" in message and "120 à 180" in message


def test_aucun_journal_quand_la_longueur_est_bonne(profil, caplog):
    with caplog.at_level("INFO", logger="denicheur.redaction.service"):
        _redacteur(Ollama(_texte(150)), profil).rediger(_offre(), SCORE, "email")
    assert [r for r in caplog.records if r.name == "denicheur.redaction.service"] == []


@pytest.mark.parametrize(
    "trou",
    ["[à compléter : détail sur l'entreprise]", "[A COMPLETER]", "[à compléter]", "[ à compléter : le nom ]"],
)
def test_aucun_trou_a_completer_ne_survit_dans_le_texte_livre(profil, trou):
    corps = f"Madame, Monsieur, je postule. {trou} " + _mots(140)
    texte = _redacteur(Ollama(corps + f"\n{LIGNE} : Python"), profil).rediger(_offre(), SCORE, "email")
    assert "[" not in texte and "compl" not in texte.lower().replace("complet", "")
    assert "je postule. mot0" in texte  # pas de double espace après le retrait


def test_les_crochets_sans_trou_sont_conserves(profil):
    corps = "Madame, Monsieur, voir [1] ci-dessous. " + _mots(140)
    texte = _redacteur(Ollama(corps + f"\n{LIGNE} : x"), profil).rediger(_offre(), SCORE, "email")
    assert "[1]" in texte


def test_phrase_d_introduction_du_modele_est_retiree(profil):
    brut = "Voici le corps de l'e-mail de candidature :\n\n" + _texte(150)
    texte = _redacteur(Ollama(brut), profil).rediger(_offre(), SCORE, "email")
    assert not texte.startswith("Voici") and texte.startswith("mot0 ")


def test_une_phrase_qui_commence_par_voici_dans_le_corps_est_conservee(profil):
    corps = "Madame, Monsieur,\nVoici mon projet : " + _mots(150)
    texte = _redacteur(Ollama(corps + f"\n{LIGNE} : x"), profil).rediger(_offre(), SCORE, "email")
    assert "Voici mon projet" in texte


def test_le_prompt_demande_le_texte_seul():
    assert "sans phrase d'introduction" in message_utilisateur(_offre(), SCORE, "email")


def test_premiere_ligne_voici_sans_deux_points_est_du_corps(profil):
    corps = "Voici ma candidature pour ce poste. " + _mots(150)
    texte = _redacteur(Ollama(corps + f"\n{LIGNE} : x"), profil).rediger(_offre(), SCORE, "email")
    assert texte.startswith("Voici ma candidature")


def test_l_identite_locale_n_entre_jamais_dans_le_prompt(profil):
    (profil / "identite.md").write_text("nom: IDENTITE-SECRETE\nemail: moi@exemple.fr\n", encoding="utf-8")
    ollama = Ollama(_texte(260))
    _redacteur(ollama, profil).rediger(_offre(), SCORE, "lettre")
    envoye = ollama.requetes[0].content.decode("utf-8")
    assert "IDENTITE-SECRETE" not in envoye and "moi@exemple.fr" not in envoye
