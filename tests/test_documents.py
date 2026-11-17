from datetime import date
from pathlib import Path

import docx
import pytest
from pypdf import PdfReader

from denicheur.messages_fr import message_accompagnement
from denicheur.models import Offre, Piste
from denicheur.redaction.documents import (
    ErreurDocuments,
    IdentiteManquante,
    Liens,
    ecrire_lettre,
    lire_identite,
    lire_liens,
    nom_fichier,
    rendre_lettre,
)

JOUR = date(2026, 11, 17)
TEXTE = (
    "Madame, Monsieur,\n\n"
    "Mon travail à l'œuvre – « test » ’ok’ … [à compléter : détail sur l'entreprise]\n\n"
    "Cordialement.\n\n"
    "⚠️ longueur hors plage\n"
    "Éléments du profil utilisés : RiftMind"
)
IDENTITE_TXT = (
    "nom: Jeanne Exemple\nadresse: 1 rue des Tests\nville: 75001 Paris\n"
    "telephone: 01 02 03 04 05\nemail: jeanne@exemple.test\n"
)


def _offre(titre="Développeur Python", entreprise="ACME"):
    return Offre(
        source="t", source_id="1", url="u", titre=titre, entreprise=entreprise, commune="Paris", lat=None,
        lon=None, piste=Piste.ALTERNANCE, duree_mois=None, debut=None, niveau_diplome=None,
        description="d", publiee_le=None, expire_le=None,
    )  # fmt: skip


@pytest.fixture
def identite(tmp_path):
    chemin = tmp_path / "identite.md"
    chemin.write_text(IDENTITE_TXT, encoding="utf-8")
    return lire_identite(chemin)


@pytest.fixture
def dossier(tmp_path):
    d = tmp_path / "lettres"
    d.mkdir()
    return d


def _texte_pdf(chemin: Path) -> str:
    return "\n".join(p.extract_text() for p in PdfReader(chemin).pages)


def _texte_docx(chemin: Path) -> str:
    return "\n".join(p.text for p in docx.Document(str(chemin)).paragraphs)


# --- identité ---
def test_lire_identite(identite):
    assert (identite.nom, identite.ville, identite.email) == (
        "Jeanne Exemple",
        "75001 Paris",
        "jeanne@exemple.test",
    )


def test_identite_absente_erreur_sans_donnee(tmp_path):
    with pytest.raises(IdentiteManquante) as e:
        lire_identite(tmp_path / "absent.md")
    assert str(tmp_path) not in str(e.value)


def test_identite_incomplete(tmp_path):
    (tmp_path / "i.md").write_text("nom: Jeanne\n", encoding="utf-8")
    with pytest.raises(IdentiteManquante):
        lire_identite(tmp_path / "i.md")


# --- fichiers ---
def test_pdf_et_docx_contiennent_en_tete_objet_corps_et_signature(identite, dossier):
    pdf, dx = ecrire_lettre(TEXTE, _offre(), identite, dossier, JOUR)
    for texte in (_texte_pdf(pdf), _texte_docx(dx)):
        assert "Jeanne Exemple" in texte and "1 rue des Tests" in texte and "jeanne@exemple.test" in texte
        assert "Paris, le 17/11/2026" in texte
        assert "Candidature pour le poste de Développeur Python" in texte
        assert "Madame, Monsieur," in texte and "Cordialement." in texte
        assert texte.strip().endswith("Jeanne Exemple")


def test_lignes_de_relecture_exclues_des_fichiers(identite, dossier):
    pdf, dx = ecrire_lettre(TEXTE, _offre(), identite, dossier, JOUR)
    for texte in (_texte_pdf(pdf), _texte_docx(dx)):
        assert "Éléments du profil" not in texte and "longueur hors plage" not in texte and "⚠" not in texte


def test_caracteres_hors_latin1_remplaces_dans_le_pdf(identite, dossier):
    pdf, dx = ecrire_lettre(TEXTE, _offre(), identite, dossier, JOUR)
    assert "oeuvre" in _texte_pdf(pdf) and "œuvre" in _texte_docx(dx)  # DOCX garde le texte d'origine


def test_les_deux_fichiers_portent_le_meme_nom_et_sont_dans_le_dossier(identite, dossier):
    pdf, dx = ecrire_lettre(TEXTE, _offre(), identite, dossier, JOUR)
    assert pdf.parent == dx.parent == dossier
    assert (pdf.name, dx.name) == ("Lettre de motivation ACME.pdf", "Lettre de motivation ACME.docx")


@pytest.mark.parametrize(
    "entreprise", ["..\\..\\evil", "../../evil", 'A<B>C:"D"|E?*', "CON", "a" * 400, "   ", "x."]
)
def test_nom_d_entreprise_hostile_reste_dans_le_dossier(identite, dossier, entreprise):
    pdf, dx = ecrire_lettre(TEXTE, _offre(entreprise=entreprise), identite, dossier, JOUR)
    for f in (pdf, dx):
        assert f.parent == dossier and f.exists()
        assert not set('<>:"/\\|?*') & set(f.name) and len(f.name) < 150
        assert not f.stem.endswith((" ", "."))


def test_entreprise_inconnue_libelle_neutre(identite, dossier):
    pdf, _ = ecrire_lettre(TEXTE, _offre(entreprise=None), identite, dossier, JOUR)
    assert pdf.name == "Lettre de motivation.pdf"


def test_jamais_d_ecrasement(identite, dossier):
    pdf, dx = ecrire_lettre(TEXTE, _offre(), identite, dossier, JOUR)
    octets = (pdf.read_bytes(), dx.read_bytes())
    pdf2, dx2 = ecrire_lettre(TEXTE + " bis", _offre(), identite, dossier, JOUR)
    assert (pdf2.name, dx2.name) == (
        "Lettre de motivation ACME (2).pdf",
        "Lettre de motivation ACME (2).docx",
    )
    assert (pdf.read_bytes(), dx.read_bytes()) == octets
    pdf3, _ = ecrire_lettre(TEXTE, _offre(), identite, dossier, JOUR)
    assert pdf3.name == "Lettre de motivation ACME (3).pdf"


def test_un_seul_fichier_existant_decale_aussi_le_second(identite, dossier):
    (dossier / "Lettre de motivation ACME.docx").write_bytes(b"perso")
    pdf, dx = ecrire_lettre(TEXTE, _offre(), identite, dossier, JOUR)
    assert pdf.name.endswith("(2).pdf") and dx.name.endswith("(2).docx")
    assert (dossier / "Lettre de motivation ACME.docx").read_bytes() == b"perso"


def test_dossier_absent_erreur_sans_chemin(identite, tmp_path):
    with pytest.raises(ErreurDocuments) as e:
        ecrire_lettre(TEXTE, _offre(), identite, tmp_path / "inexistant", JOUR)
    assert str(tmp_path) not in str(e.value)
    assert not (tmp_path / "inexistant").exists()


def test_nom_fichier():
    assert nom_fichier("ACME") == "Lettre de motivation ACME"
    assert nom_fichier(None) == "Lettre de motivation"


def test_titre_a_plusieurs_lignes_sur_une_seule_ligne_d_objet(identite, dossier):
    pdf, _ = ecrire_lettre(TEXTE, _offre(titre="Dev\r\nweb"), identite, dossier, JOUR)
    assert "Candidature pour le poste de Dev web" in _texte_pdf(pdf)


# --- message d'accompagnement ---
def test_message_accompagnement_gabarit_fixe():
    m = message_accompagnement("Développeur web", "ACME", "Jeanne Exemple")
    assert "Développeur web" in m and "ACME" in m and "ci-joint" in m
    assert m.startswith("Madame, Monsieur,") and m.rstrip().endswith("Jeanne Exemple")


def test_message_accompagnement_sans_entreprise():
    m = message_accompagnement("Développeur web", None, "Jeanne Exemple")
    assert "Développeur web" in m and "None" not in m


def test_course_entre_la_verification_et_l_ecriture_n_ecrase_rien(identite, dossier, monkeypatch):
    (dossier / "Lettre de motivation ACME.pdf").write_bytes(b"perso")
    monkeypatch.setattr(Path, "exists", lambda self: False)  # la vérification est trompée
    with pytest.raises(ErreurDocuments):
        ecrire_lettre(TEXTE, _offre(), identite, dossier, JOUR)
    assert (dossier / "Lettre de motivation ACME.pdf").read_bytes() == b"perso"


def test_destinataire_present_seulement_avec_une_entreprise(identite, dossier):
    pdf, dx = ecrire_lettre(TEXTE, _offre(), identite, dossier, JOUR)
    assert "service recrutement, ACME" in _texte_pdf(pdf) and "service recrutement, ACME" in _texte_docx(dx)
    pdf2, _ = ecrire_lettre(TEXTE, _offre(entreprise=None), identite, dossier, JOUR)
    assert "service recrutement" not in _texte_pdf(pdf2)


def test_rendre_lettre_en_memoire_n_ecrit_rien(identite, dossier):
    pdf, dx = rendre_lettre(TEXTE, _offre(), identite, JOUR)
    assert pdf.startswith(b"%PDF") and dx.startswith(b"PK")  # un DOCX est une archive zip
    assert list(dossier.iterdir()) == []


# --- liens vers les projets ---
LIENS_TXT = (
    "github: https://github.com/jeanne-exemple/\n"
    "linkedin: https://www.linkedin.com/in/jeanne-exemple/\n"
    "projet RiftMind: https://github.com/jeanne-exemple/riftmind\n"
    "projet assistant boursier: https://github.com/jeanne-exemple/finance\n"
)
TEXTE_RIFTMIND = (
    "Madame, Monsieur,\n\nJ'ai développé RiftMind en Rust.\n\nCordialement.\n\n"
    "Éléments du profil utilisés : RiftMind"
)


@pytest.fixture
def liens(tmp_path):
    chemin = tmp_path / "liens.md"
    chemin.write_text(LIENS_TXT, encoding="utf-8")
    return lire_liens(chemin)


def test_liens_absents_pas_d_erreur_et_rien_a_ajouter(tmp_path):
    assert lire_liens(tmp_path / "absent.md") == Liens()


def test_lire_liens(liens):
    assert liens.github == "https://github.com/jeanne-exemple/"
    assert liens.linkedin == "https://www.linkedin.com/in/jeanne-exemple/"
    assert dict(liens.projets) == {
        "riftmind": "https://github.com/jeanne-exemple/riftmind",
        "assistant boursier": "https://github.com/jeanne-exemple/finance",
    }


def test_le_lien_du_projet_cite_et_les_profils_suivent_la_signature(identite, dossier, liens):
    pdf, dx = ecrire_lettre(TEXTE_RIFTMIND, _offre(), identite, dossier, JOUR, liens)
    for texte in (_texte_pdf(pdf), _texte_docx(dx)):
        fin = texte[texte.index("Jeanne Exemple", texte.index("Cordialement")) :]
        assert "https://github.com/jeanne-exemple/riftmind" in fin
        assert "GitHub : https://github.com/jeanne-exemple/" in fin
        assert "LinkedIn : https://www.linkedin.com/in/jeanne-exemple/" in fin
        assert "finance" not in texte  # le projet non cité n'a pas de lien


def test_la_recherche_du_projet_ignore_la_casse(identite, dossier, liens):
    pdf, _ = ecrire_lettre(
        TEXTE_RIFTMIND.replace("RiftMind en", "RIFTMIND en"), _offre(), identite, dossier, JOUR, liens
    )
    assert "jeanne-exemple/riftmind" in _texte_pdf(pdf)


def test_aucun_projet_cite_seulement_les_profils(identite, dossier, liens):
    pdf, _ = ecrire_lettre(TEXTE, _offre(), identite, dossier, JOUR, liens)
    texte = _texte_pdf(pdf)
    assert "riftmind" not in texte and "linkedin.com/in/jeanne-exemple" in texte


def test_sans_liens_la_signature_reste_la_derniere_ligne(identite, dossier):
    pdf, dx = ecrire_lettre(TEXTE_RIFTMIND, _offre(), identite, dossier, JOUR)
    for texte in (_texte_pdf(pdf), _texte_docx(dx)):
        assert texte.strip().endswith("Jeanne Exemple") and "http" not in texte


def test_les_liens_ne_viennent_jamais_de_la_ligne_de_profil(identite, dossier, liens):
    brut = "Madame, Monsieur,\n\nBonjour.\n\nÉléments du profil utilisés : RiftMind"
    pdf, _ = ecrire_lettre(brut, _offre(), identite, dossier, JOUR, liens)
    assert "riftmind" not in _texte_pdf(pdf)
