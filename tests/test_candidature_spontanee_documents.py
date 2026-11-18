from datetime import date

import docx
import pytest
from pypdf import PdfReader

from denicheur.messages_fr import accompagnement_telegram, message_accompagnement
from denicheur.models import Entreprise, Offre, Piste
from denicheur.redaction.cible import Cible
from denicheur.redaction.documents import ecrire_lettre, lire_identite, rendre_lettre
from denicheur.redaction.gmail_drafts import sujet_brouillon

JOUR = date(2026, 11, 18)
TEXTE = (
    "Madame, Monsieur,\n\nVotre activité m'intéresse.\n\nCordialement.\n\n"
    "Éléments du profil utilisés : RiftMind"
)


@pytest.fixture
def identite(tmp_path):
    chemin = tmp_path / "identite.md"
    chemin.write_text(
        "nom: Jeanne Exemple\nadresse: 1 rue des Tests\nville: 75001 Paris\n"
        "telephone: 01 02 03 04 05\nemail: jeanne@exemple.test\n",
        encoding="utf-8",
    )
    return lire_identite(chemin)


@pytest.fixture
def dossier(tmp_path):
    d = tmp_path / "lettres"
    d.mkdir()
    return d


def _offre(titre="Développeur Python", entreprise="ACME"):
    return Offre(
        source="t", source_id="1", url="u", titre=titre, entreprise=entreprise, commune="Paris", lat=None,
        lon=None, piste=Piste.ALTERNANCE, duree_mois=None, debut=None, niveau_diplome=None,
        description="d", publiee_le=None, expire_le=None,
    )  # fmt: skip


def _texte_pdf(octets_ou_chemin):
    return "\n".join(p.extract_text() for p in PdfReader(octets_ou_chemin).pages)


def _texte_docx(chemin):
    return "\n".join(p.text for p in docx.Document(str(chemin)).paragraphs)


def test_cible_depuis_une_offre_et_depuis_une_entreprise():
    assert Cible.depuis_offre(_offre()) == Cible("ACME", "Développeur Python")
    e = Entreprise(siret="12345678900011", nom="SKAIZEN GROUP", origine="csv")
    assert Cible.depuis_entreprise(e) == Cible("SKAIZEN GROUP", None)


def test_objet_spontane_sans_poste_dans_le_pdf_et_le_docx(identite, dossier):
    pdf, docx_ = ecrire_lettre(TEXTE, Cible("ACME"), identite, dossier, JOUR)
    for texte in (_texte_pdf(pdf), _texte_docx(docx_)):
        assert "Objet : Candidature spontanée" in texte
        assert "pour le poste" not in texte
        assert "À l'attention du service recrutement, ACME" in texte
        assert "Votre activité m'intéresse." in texte and "Éléments du profil" not in texte


def test_fichiers_d_entreprise_nommes_comme_les_autres_sans_ecrasement(identite, dossier):
    a = ecrire_lettre(TEXTE, Cible("ACME"), identite, dossier, JOUR)
    b = ecrire_lettre(TEXTE, Cible("ACME"), identite, dossier, JOUR)
    assert [p.name for p in a] == ["Lettre de motivation ACME.pdf", "Lettre de motivation ACME.docx"]
    assert [p.name for p in b] == ["Lettre de motivation ACME (2).pdf", "Lettre de motivation ACME (2).docx"]


def test_nom_d_entreprise_hostile_reste_dans_le_dossier(identite, dossier):
    pdf, docx_ = ecrire_lettre(TEXTE, Cible("..\\..\\evil/<x>:"), identite, dossier, JOUR)
    assert pdf.parent == dossier and docx_.parent == dossier


def test_entreprise_sans_nom_pas_de_destinataire(identite):
    texte = _texte_pdf_depuis_octets(rendre_lettre(TEXTE, Cible(None), identite, JOUR)[0])
    assert "service recrutement" not in texte and "Objet : Candidature spontanée" in texte


def _texte_pdf_depuis_octets(octets):
    import io

    return _texte_pdf(io.BytesIO(octets))


def test_une_offre_garde_son_objet_avec_le_poste(identite):
    texte = _texte_pdf_depuis_octets(rendre_lettre(TEXTE, _offre(), identite, JOUR)[0])
    assert "Objet : Candidature pour le poste de Développeur Python" in texte


@pytest.mark.parametrize("type_", ["spontanee", "lettre"])
def test_sujet_gmail_spontane(type_):
    assert sujet_brouillon(type_, Cible("ACME")) == "Candidature spontanée : ACME"
    assert sujet_brouillon(type_, Cible(None)) == "Candidature spontanée"


def test_sujet_gmail_spontane_nettoye_d_un_faux_en_tete():
    s = sujet_brouillon("spontanee", Cible("ACME\r\nBcc: pirate@exemple.test"))
    assert "\n" not in s and "\r" not in s


def test_sujet_d_une_offre_inchange():
    assert sujet_brouillon("email", _offre()) == "Candidature : Développeur Python"
    assert sujet_brouillon("relance", _offre()) == "Relance : candidature Développeur Python"


def test_message_d_accompagnement_spontane_gabarit_fixe():
    m = message_accompagnement(None, "ACME", "Jeanne Exemple")
    assert m == (
        "Madame, Monsieur,\n\n"
        "Veuillez trouver ci-joint ma lettre de motivation pour une candidature spontanée "
        "au sein de ACME.\n\n"
        "Je reste disponible pour un échange.\n\n"
        "Cordialement,\nJeanne Exemple"
    )


def test_message_d_accompagnement_spontane_sans_entreprise():
    m = message_accompagnement(None, None, "Jeanne Exemple")
    assert "pour une candidature spontanée." in m and "au sein de" not in m and "poste" not in m


def test_message_d_accompagnement_d_une_offre_inchange():
    m = message_accompagnement("Développeur web", "ACME", "Jeanne Exemple")
    assert "pour le poste de Développeur web au sein de ACME" in m


def test_message_telegram_spontane_echappe_le_html():
    m = accompagnement_telegram(None, "A&B <i>", "Jeanne Exemple")
    assert "A&amp;B &lt;i&gt;" in m and "<i>" not in m
