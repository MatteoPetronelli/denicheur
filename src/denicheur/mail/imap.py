import email
import email.policy
import imaplib
from collections.abc import Callable
from datetime import datetime
from email.message import Message
from typing import Any

LIBELLE = "Denicheur"
_MOIS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


class ErreurImap(Exception):
    """Erreur IMAP sans détail susceptible de contenir le mot de passe."""


def _gmail() -> Any:
    return imaplib.IMAP4_SSL("imap.gmail.com")


def _date_imap(d: datetime) -> str:
    # strftime("%b") dépend de la locale ; IMAP exige les mois anglais.
    return f"{d.day:02d}-{_MOIS[d.month - 1]}-{d.year}"


def lire_alertes(
    user: str,
    password: str,
    since: datetime,
    imap_factory: Callable[[], Any] = _gmail,
) -> list[Message]:
    """Lit le libellé Denicheur en lecture seule (BODY.PEEK : rien n'est marqué lu)."""
    imap = imap_factory()
    selectionne = False
    try:
        try:
            imap.login(user, password)
        except Exception:
            raise ErreurImap("Connexion IMAP refusée") from None
        statut, _ = imap.select(LIBELLE, readonly=True)
        if statut != "OK":  # imaplib ne lève pas : un libellé mal nommé donnerait zéro offre en silence
            raise ErreurImap(f"Libellé Gmail « {LIBELLE} » introuvable")
        selectionne = True
        _, data = imap.uid("SEARCH", None, "SINCE", _date_imap(since))
        messages: list[Message] = []
        for uid in data[0].split():
            _, morceaux = imap.uid("FETCH", uid, "(BODY.PEEK[])")
            brut = morceaux[0][1]
            messages.append(email.message_from_bytes(brut, policy=email.policy.default))
        return messages
    finally:
        if selectionne:
            imap.close()
        imap.logout()
