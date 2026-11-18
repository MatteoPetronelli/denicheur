import httpx
import pytest
from test_redaction import (  # noqa: F401 : fixtures et faux serveur partagés avec les tests des offres
    EMAIL,
    LIGNE,
    TEL,
    Ollama,
    _horloge,
    _redacteur,
    _texte,
    cfg,
)

from denicheur.models import Entreprise
from denicheur.redaction.prompts import (
    ProfilManquant,
    message_systeme,
    message_utilisateur_entreprise,
)
from denicheur.redaction.service import Redacteur
from denicheur.scoring.llm import OllamaIndisponible


def _ent(**kw):
    base = {
        "siret": "83465065700010", "nom": "SKAIZEN GROUP", "activite": "Conseil en systèmes et logiciels",
        "naf": "62.02A", "effectif": "10-19", "adresse": "22 AVENUE DE LA TERRASSE 78360 MONTESSON",
        "commune": "MONTESSON", "lat": 48.9, "lon": 2.1, "distance_km": 4.7, "priorite": 1,
        "url_candidature": "https://lba.example/skaizen", "origine": "csv",
    }  # fmt: skip
    return Entreprise(**{**base, **kw})


# --- prompts ---
def test_message_spontane_donne_nom_activite_commune_et_la_plage_du_message():
    m = message_utilisateur_entreprise(_ent(), "spontanee")
    assert "Entreprise : SKAIZEN GROUP" in m
    assert "Activité : Conseil en systèmes et logiciels" in m
    assert "Lieu : MONTESSON" in m
    assert "de 120 à 180 mots" in m and "vise 150 mots, jamais moins de 120" in m
    assert "candidature spontanée" in m and "pas d'offre en cours" in m


def test_message_de_lettre_spontanee_vise_250_a_300_mots():
    m = message_utilisateur_entreprise(_ent(), "lettre")
    assert "de 250 à 300 mots" in m and "vise 275 mots, jamais moins de 250" in m
    assert "lettre de motivation" in m and "candidature spontanée" in m


@pytest.mark.parametrize("type_", ["spontanee", "lettre"])
def test_disponibilite_en_alternance_et_aucune_phrase_de_stage(type_):
    m = message_utilisateur_entreprise(_ent(), type_)
    assert "une semaine d'école pour deux semaines en entreprise" in m and "dès que possible" in m
    assert "stage" not in m.lower() and "janvier" not in m.lower()


@pytest.mark.parametrize("type_", ["spontanee", "lettre"])
def test_le_modele_choisit_le_projet_et_n_invente_rien(type_):
    m = message_utilisateur_entreprise(_ent(), type_)
    assert "projet du profil le plus proche de l'activité" in m
    assert "tu ne sais rien d'autre" in m.lower() and "n'invente" in m
    assert "aucun texte entre crochets" in m and "sans phrase d'introduction" in m
    assert f"« {LIGNE} : … »" in m


@pytest.mark.parametrize("type_", ["spontanee", "lettre"])
def test_aucun_poste_n_est_invente(type_):
    m = message_utilisateur_entreprise(_ent(), type_)
    assert "ne cite aucun intitulé de poste" in m and "alternance en développement" in m


def test_le_prompt_ne_contient_que_nom_activite_et_commune():
    m = message_utilisateur_entreprise(_ent(), "spontanee")
    for interdit in (
        "83465065700010",
        "62.02A",
        "10-19",
        "AVENUE DE LA TERRASSE",
        "4.7",
        "lba.example",
        "48.9",
    ):
        assert interdit not in m


def test_contacts_du_nom_et_de_l_activite_masques_et_lignes_uniques():
    m = message_utilisateur_entreprise(
        _ent(nom="ACME\ncontact@acme.test 01 02 03 04 05", activite="x\r\ny moi@exemple.fr"), "spontanee"
    )
    assert not EMAIL.search(m.split("Activité")[0].replace("moi@", "")) or "[contact]" in m
    assert "contact@acme.test" not in m and "moi@exemple.fr" not in m and not TEL.search(m)
    assert "Entreprise : ACME [contact] [contact]" in m


def test_champs_absents_donnent_une_mention_neutre():
    m = message_utilisateur_entreprise(_ent(activite=None, commune=None), "spontanee")
    assert "Activité : non précisée" in m and "Lieu : non précisé" in m


def test_nom_et_activite_bornes():
    m = message_utilisateur_entreprise(_ent(nom="N" * 5000, activite="A" * 5000), "spontanee")
    assert len(m) < 3000


@pytest.mark.parametrize("type_", ["relance", "email", "inconnu", ""])
def test_types_non_spontanes_refuses_pour_une_entreprise(type_):
    with pytest.raises(ValueError):
        message_utilisateur_entreprise(_ent(), type_)


# --- service ---
def test_rediger_entreprise_renvoie_le_texte_avec_la_ligne_de_profil(profil):
    ollama = Ollama(_texte(150))
    texte = _redacteur(ollama, profil).rediger_entreprise(_ent(), "spontanee")
    assert texte.endswith(f"{LIGNE} : RiftMind, Python") and len(ollama.requetes) == 1


def test_requete_avec_le_modele_et_les_options_de_la_config_et_les_trois_fichiers(profil):
    ollama = Ollama(_texte(150))
    _redacteur(ollama, profil).rediger_entreprise(_ent(), "spontanee")
    corps = ollama.corps()
    e = cfg.llm.ecriture
    assert corps["model"] == e.modele
    assert corps["options"] == {"temperature": e.temperature, "num_ctx": e.num_ctx}
    systeme, utilisateur = corps["messages"][0]["content"], corps["messages"][1]["content"]
    assert systeme == message_systeme(profil) and "CV-SECRET" not in systeme + utilisateur
    assert "Entreprise : SKAIZEN GROUP" in utilisateur


@pytest.mark.parametrize("type_", ["relance", "email", "inconnu"])
def test_type_refuse_sans_appel_au_modele(profil, type_):
    ollama = Ollama()
    with pytest.raises(ValueError):
        _redacteur(ollama, profil).rediger_entreprise(_ent(), type_)
    assert ollama.requetes == []


def test_profil_manquant_leve_avant_l_appel(profil):
    (profil / "profil.md").unlink()
    ollama = Ollama()
    with pytest.raises(ProfilManquant):
        _redacteur(ollama, profil).rediger_entreprise(_ent(), "spontanee")
    assert ollama.requetes == []


def test_trou_a_completer_retire(profil):
    brut = _texte(150).replace("mot3", "[à compléter : détail sur l'entreprise]")
    texte = _redacteur(Ollama(brut), profil).rediger_entreprise(_ent(), "spontanee")
    assert "compléter" not in texte and "[" not in texte


def test_un_seul_second_essai_si_le_texte_est_trop_court_et_rapide(profil):
    ollama = Ollama(_texte(60), _texte(150, tag="bon"))
    texte = _redacteur(ollama, profil, _horloge(0, 10, 10, 20)).rediger_entreprise(_ent(), "spontanee")
    assert len(ollama.requetes) == 2 and "bon0" in texte
    assert "refais-le avec 120 à 180 mots" in ollama.corps(1)["messages"][1]["content"]


def test_lettre_d_entreprise_vise_250_300_mots(profil):
    ollama = Ollama(_texte(275))
    _redacteur(ollama, profil).rediger_entreprise(_ent(), "lettre")
    assert len(ollama.requetes) == 1


def test_ollama_arrete_leve_ollama_indisponible(profil):
    ollama = Ollama(httpx.ConnectError("refusé"))
    with pytest.raises(OllamaIndisponible):
        _redacteur(ollama, profil).rediger_entreprise(_ent(), "spontanee")


def test_redacteur_est_bien_la_meme_classe(profil):
    assert isinstance(_redacteur(Ollama(), profil), Redacteur)
