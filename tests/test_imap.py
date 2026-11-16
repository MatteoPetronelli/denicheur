from datetime import datetime
from email.message import Message

import pytest

from denicheur.mail.imap import ErreurImap, lire_alertes

SINCE = datetime(2026, 11, 9, 8, 0)
MOT_DE_PASSE = "abcd efgh ijkl mnop"
AUTORISEES = {"login", "select", "uid_search", "uid_fetch", "close", "logout"}


def _mail(sujet: str) -> bytes:
    return f"From: alertes@exemple.fr\r\nSubject: {sujet}\r\n\r\nCorps\r\n".encode()


class FauxImap:
    """Faux serveur IMAP : journalise chaque commande, refuse toute commande d'écriture."""

    def __init__(
        self, messages: dict[bytes, bytes], *, echec_fetch=False, echec_login=False, libelle_absent=False
    ):
        self.libelle_absent = libelle_absent
        self.messages = messages
        self.echec_fetch = echec_fetch
        self.echec_login = echec_login
        self.journal: list[str] = []
        self.selections: list[tuple[str, bool]] = []
        self.recherches: list[tuple] = []
        self.fetchs: list[str] = []

    def login(self, user, password):
        self.journal.append("login")
        if self.echec_login:
            raise OSError(f"LOGIN failed for {user} / {password}")
        return "OK", [b"ok"]

    def select(self, mailbox="INBOX", readonly=False):
        self.journal.append("select")
        self.selections.append((mailbox, readonly))
        if self.libelle_absent:
            return "NO", [b"[NONEXISTENT] Unknown Mailbox"]
        return "OK", [b"2"]

    def uid(self, commande, *args):
        commande = commande.upper()
        if commande == "SEARCH":
            self.journal.append("uid_search")
            self.recherches.append(args)
            return "OK", [b" ".join(self.messages)]
        if commande == "FETCH":
            self.journal.append("uid_fetch")
            self.fetchs.append(args[1])
            if self.echec_fetch:
                raise OSError("connexion coupée")
            return "OK", [(b"1 (UID 1 BODY[] {1}", self.messages[args[0]]), b")"]
        raise AssertionError(f"commande interdite : UID {commande}")

    def close(self):
        self.journal.append("close")
        return "OK", [b"ok"]

    def logout(self):
        self.journal.append("logout")
        return "BYE", [b"bye"]

    def __getattr__(self, nom):  # store, copy, expunge, append, delete… : tout est interdit
        raise AssertionError(f"commande interdite : {nom}")


def _faux(**kw) -> FauxImap:
    return FauxImap({b"1": _mail("Alternance dev"), b"2": _mail("Stage data")}, **kw)


def test_deux_messages_retournes():
    faux = _faux()
    messages = lire_alertes("moi@exemple.fr", MOT_DE_PASSE, SINCE, imap_factory=lambda: faux)
    assert len(messages) == 2
    assert all(isinstance(m, Message) for m in messages)
    assert [m["Subject"] for m in messages] == ["Alternance dev", "Stage data"]


def test_recherche_depuis_since_au_format_imap():
    faux = _faux()
    lire_alertes("moi@exemple.fr", MOT_DE_PASSE, SINCE, imap_factory=lambda: faux)
    assert faux.recherches == [(None, "SINCE", "09-Nov-2026")]


def test_boite_intacte_lecture_seule_et_peek():
    faux = _faux()
    lire_alertes("moi@exemple.fr", MOT_DE_PASSE, SINCE, imap_factory=lambda: faux)
    assert faux.selections == [("Denicheur", True)]
    assert faux.fetchs and all("BODY.PEEK" in f for f in faux.fetchs)
    assert set(faux.journal) <= AUTORISEES


def test_session_fermee_si_fetch_echoue():
    faux = _faux(echec_fetch=True)
    with pytest.raises(OSError, match="connexion coupée"):
        lire_alertes("moi@exemple.fr", MOT_DE_PASSE, SINCE, imap_factory=lambda: faux)
    assert faux.journal[-2:] == ["close", "logout"]


def test_login_refuse_ne_fuite_pas_le_mot_de_passe():
    faux = _faux(echec_login=True)
    with pytest.raises(ErreurImap) as exc:
        lire_alertes("moi@exemple.fr", MOT_DE_PASSE, SINCE, imap_factory=lambda: faux)
    assert MOT_DE_PASSE not in str(exc.value)
    assert exc.value.__cause__ is None
    assert exc.value.__suppress_context__
    assert "logout" in faux.journal
    assert "close" not in faux.journal


def test_libelle_absent_leve_une_erreur_claire():
    faux = _faux(libelle_absent=True)
    with pytest.raises(ErreurImap, match="Denicheur"):
        lire_alertes("moi@exemple.fr", MOT_DE_PASSE, SINCE, imap_factory=lambda: faux)
    assert faux.recherches == []
    assert faux.journal[-1] == "logout"
