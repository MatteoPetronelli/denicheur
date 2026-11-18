"""Lettre de motivation en PDF et DOCX. L'identité du candidat n'est lue qu'ici, jamais par un prompt."""

import io
import re
from datetime import date
from pathlib import Path
from typing import NamedTuple

import docx
from fpdf import FPDF

from denicheur.models import Offre
from denicheur.redaction.cible import Cible, en_cible
from denicheur.redaction.gmail_drafts import corps_pour_gmail
from denicheur.redaction.prompts import PROFILE

IDENTITE = PROFILE / "identite.md"
LIENS = PROFILE / "liens.md"
# Valeur par défaut ; `LETTRES_DIR` dans l'environnement la remplace.
DOSSIER_LETTRES = Path.home() / "Desktop" / "Matteo" / "lettres motivation taf"
_CHAMPS = ("nom", "adresse", "ville", "telephone", "email")
_INTERDITS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_LATIN1 = str.maketrans({
    "œ": "oe", "Œ": "Oe", "’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-", "…": "...",
    "€": "EUR", " ": " ", " ": " ",
})  # fmt: skip
MAX_ENTREPRISE = 80


class ErreurDocuments(Exception):
    """Échec de génération ou d'écriture ; le message ne contient ni chemin ni donnée personnelle."""


class IdentiteManquante(ErreurDocuments):
    pass


class Identite(NamedTuple):
    nom: str
    adresse: str
    ville: str
    telephone: str
    email: str


def lire_identite(chemin: Path = IDENTITE) -> Identite:
    try:
        lignes = chemin.read_text(encoding="utf-8").splitlines()
    except OSError:
        raise IdentiteManquante("Fichier d'identité introuvable (profile/identite.md)") from None
    valeurs = {}
    for ligne in lignes:
        cle, _, valeur = ligne.partition(":")
        if valeur.strip():
            valeurs[cle.strip().lower()] = valeur.strip()
    if any(c not in valeurs for c in _CHAMPS):
        raise IdentiteManquante("Fichier d'identité incomplet (profile/identite.md)")
    return Identite(*(valeurs[c] for c in _CHAMPS))


class Liens(NamedTuple):
    """Liens publics ajoutés sous la signature, comme dans les lettres d'origine."""

    projets: tuple[tuple[str, str], ...] = ()  # (mot-clé en minuscules, URL)
    github: str | None = None
    linkedin: str | None = None


SANS_LIENS = Liens()


def lire_liens(chemin: Path = LIENS) -> Liens:
    """Fichier facultatif : `github:`, `linkedin:` et `projet <mot-clé>:` suivis d'une URL."""
    try:
        lignes = chemin.read_text(encoding="utf-8").splitlines()
    except OSError:
        return Liens()
    projets: list[tuple[str, str]] = []
    autres: dict[str, str] = {}
    for ligne in lignes:
        cle, _, url = ligne.partition(":")
        cle, url = cle.strip().lower(), url.strip()
        if not url:
            continue
        if cle.startswith("projet "):
            projets.append((cle.removeprefix("projet ").strip(), url))
        else:
            autres[cle] = url
    return Liens(tuple(projets), autres.get("github"), autres.get("linkedin"))


def _lignes_liens(corps: str, liens: Liens) -> list[str]:
    bas = corps.lower()
    lignes = [f"Projet : {url}" for mot, url in liens.projets if mot in bas]
    if liens.github:
        lignes.append(f"GitHub : {liens.github}")
    if liens.linkedin:
        lignes.append(f"LinkedIn : {liens.linkedin}")
    return lignes


def _une_ligne(texte: str) -> str:
    return " ".join(texte.split())


def _assainir(texte: str) -> str:
    propre = _une_ligne(_INTERDITS.sub(" ", texte))
    return propre[:MAX_ENTREPRISE].strip(" .")


def nom_fichier(entreprise: str | None) -> str:
    e = _assainir(entreprise or "")
    return f"Lettre de motivation {e}" if e else "Lettre de motivation"


def _latin1(texte: str) -> str:
    return texte.translate(_LATIN1).encode("latin-1", "replace").decode("latin-1")


def _contenu(
    contenu: str, offre: Offre | Cible, identite: Identite, jour: date
) -> tuple[list[str], str, str, list[str]]:
    cible = en_cible(offre)
    lieu = re.sub(r"^\d+\s*", "", identite.ville)
    entete = [identite.nom, identite.adresse, identite.ville, identite.telephone, identite.email]
    destinataire = (
        [f"À l'attention du service recrutement, {_une_ligne(cible.entreprise)}"] if cible.entreprise else []
    )
    objet = (
        f"Objet : Candidature pour le poste de {_une_ligne(cible.poste)}"
        if cible.poste
        else "Objet : Candidature spontanée"
    )
    paragraphes = [p.strip() for p in corps_pour_gmail(contenu).split("\n\n") if p.strip()]
    return entete + [""] + destinataire, f"{lieu}, le {jour:%d/%m/%Y}", objet, paragraphes


def _pdf(entete: list[str], lieu_date: str, objet: str, paragraphes: list[str], fin: list[str]) -> bytes:
    pdf = FPDF(format="A4")
    pdf.set_margins(25, 20, 25)
    pdf.add_page()

    def ecrire(texte: str, style: str = "", apres: float = 0) -> None:
        pdf.set_font("Helvetica", style, 11)
        pdf.multi_cell(0, 5.5, _latin1(texte), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(apres)

    ecrire(entete[0], "B")
    for ligne in entete[1:]:
        ecrire(ligne)
    ecrire(lieu_date, apres=4)
    ecrire(objet, "B", apres=4)
    for p in paragraphes:
        ecrire(p, apres=3)
    ecrire(fin[0], "B")  # la signature, puis les liens
    for ligne in fin[1:]:
        ecrire(ligne)
    return bytes(pdf.output())


def _docx(entete: list[str], lieu_date: str, objet: str, paragraphes: list[str], fin: list[str]) -> bytes:
    doc = docx.Document()
    doc.add_paragraph().add_run(entete[0]).bold = True
    for ligne in entete[1:]:
        doc.add_paragraph(ligne)
    doc.add_paragraph(lieu_date)
    doc.add_paragraph().add_run(objet).bold = True
    for p in paragraphes:
        doc.add_paragraph(p)
    doc.add_paragraph().add_run(fin[0]).bold = True
    for ligne in fin[1:]:
        doc.add_paragraph(ligne)
    tampon = io.BytesIO()
    doc.save(tampon)
    return tampon.getvalue()


def rendre_lettre(
    contenu: str, offre: Offre | Cible, identite: Identite, jour: date, liens: Liens = SANS_LIENS
) -> tuple[bytes, bytes]:
    """(PDF, DOCX) en mémoire : rien n'est écrit sur le disque."""
    entete, lieu_date, objet, paragraphes = _contenu(contenu, offre, identite, jour)
    fin = [identite.nom, *_lignes_liens("\n".join(paragraphes), liens)]
    return (
        _pdf(entete, lieu_date, objet, paragraphes, fin),
        _docx(entete, lieu_date, objet, paragraphes, fin),
    )


def ecrire_lettre(
    contenu: str,
    offre: Offre | Cible,
    identite: Identite,
    dossier: Path,
    jour: date,
    liens: Liens = SANS_LIENS,
) -> tuple[Path, Path]:
    """Écrit `<nom>.pdf` et `<nom>.docx` dans `dossier` sans jamais écraser un fichier existant."""
    if not dossier.is_dir():
        raise ErreurDocuments("Dossier des lettres introuvable")
    octets = rendre_lettre(contenu, offre, identite, jour, liens)
    base = nom_fichier(en_cible(offre).entreprise)
    try:
        for n in range(1, 1000):
            suffixe = "" if n == 1 else f" ({n})"
            chemins = (dossier / f"{base}{suffixe}.pdf", dossier / f"{base}{suffixe}.docx")
            if any(c.exists() for c in chemins):
                continue
            # shortcut: un seul écrivain ; une course entre les deux écritures laisserait un PDF seul.
            for chemin, contenu_fichier in zip(chemins, octets, strict=True):
                with open(chemin, "xb") as f:
                    f.write(contenu_fichier)
            return chemins
    except OSError:
        raise ErreurDocuments("Écriture impossible dans le dossier des lettres") from None
    raise ErreurDocuments("Trop de lettres portant le même nom")
