"""Dépôt d'un brouillon dans Gmail par IMAP APPEND. Aucun envoi : ni SMTP, ni lecture de messages."""

import imaplib
import re
import time
from collections.abc import Callable
from email.message import EmailMessage
from typing import Any

from denicheur.models import Offre
from denicheur.redaction.prompts import LIGNE_PROFIL

_DOSSIER = re.compile(r'\(([^)]*)\)\s+(?:"[^"]*"|NIL)\s+(.+)')


class ErreurGmail(Exception):
    """Erreur IMAP sans détail susceptible de contenir l'adresse ou le mot de passe."""


def _gmail() -> Any:
    return imaplib.IMAP4_SSL("imap.gmail.com")


def _ligne(texte: str) -> str:
    return " ".join(texte.split())  # un en-tête tient sur une seule ligne


def sujet_brouillon(type_: str, offre: Offre) -> str:
    titre = _ligne(offre.titre)
    return f"Relance : candidature {titre}" if type_ == "relance" else f"Candidature : {titre}"


def corps_pour_gmail(contenu: str) -> str:
    """Le texte relu moins ce qui n'est destiné qu'à la relecture : ligne de profil et note de longueur."""
    lignes = [ligne for ligne in contenu.splitlines() if not ligne.startswith((LIGNE_PROFIL, "⚠️"))]
    return "\n".join(lignes).strip()


def _dossier_brouillons(imap: Any) -> str:
    statut, lignes = imap.list()
    if statut != "OK":
        raise ErreurGmail("Liste des dossiers Gmail refusée")
    for brut in lignes:
        if not isinstance(brut, bytes):
            continue
        m = _DOSSIER.match(brut.decode("utf-8", errors="replace"))
        if m and "\\Drafts" in m.group(1).split():
            return m.group(2).strip().strip('"')
    raise ErreurGmail("Dossier des brouillons Gmail introuvable")


def creer_brouillon(
    user: str,
    password: str,
    sujet: str,
    corps: str,
    a: str = "",
    imap_factory: Callable[[], Any] = _gmail,
) -> None:
    """Ajoute exactement un message au dossier des brouillons (attribut \\Drafts, toute langue)."""
    message = EmailMessage()
    message["Subject"] = _ligne(sujet)
    if a:
        message["To"] = _ligne(a)
    message.set_content(corps)
    imap = imap_factory()
    try:
        try:
            imap.login(user, password)
        except Exception:
            raise ErreurGmail("Connexion IMAP refusée") from None
        dossier = _dossier_brouillons(imap)
        try:
            statut, _ = imap.append(
                dossier, "(\\Draft)", imaplib.Time2Internaldate(time.time()), message.as_bytes()
            )
        except Exception:
            raise ErreurGmail("Dépôt du brouillon refusé") from None
        if statut != "OK":
            raise ErreurGmail("Dépôt du brouillon refusé")
    finally:
        imap.logout()
