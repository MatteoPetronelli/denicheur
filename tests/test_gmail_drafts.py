import ast
import email
import email.policy
import imaplib
from pathlib import Path

import pytest

from denicheur.models import Offre, Piste
from denicheur.redaction.gmail_drafts import (
    ErreurGmail,
    Piece,
    corps_pour_gmail,
    creer_brouillon,
    sujet_brouillon,
)

SRC = Path(__file__).parent.parent / "src" / "denicheur"
USER, MDP = "moi@exemple.fr", "mdp-app-secret"
FR = [
    b'(\\HasNoChildren) "/" "INBOX"',
    b'(\\HasNoChildren \\Drafts) "/" "[Gmail]/Brouillons"',
    b'(\\HasNoChildren \\Sent) "/" "[Gmail]/Messages envoy&AOk-s"',
]


class FauxImap:
    """Seules login, list, append et logout existent : toute autre méthode (select, uid, store…) échoue."""

    def __init__(self, dossiers=FR, *, login="ok", append="OK", liste="OK"):
        self.dossiers, self.mode_login, self.mode_append, self.mode_liste = dossiers, login, append, liste
        self.appels: list[tuple] = []

    def login(self, user, mdp):
        self.appels.append(("login",))
        if self.mode_login == "refus":
            raise imaplib.IMAP4.error(f"AUTHENTICATIONFAILED {user} {mdp}")
        return ("OK", [b"ok"])

    def list(self):
        self.appels.append(("list",))
        return (self.mode_liste, list(self.dossiers))

    def append(self, boite, drapeaux, date, message):
        self.appels.append(("append", boite, drapeaux, message))
        if self.mode_append == "erreur":
            raise imaplib.IMAP4.error(f"boom {USER} {MDP}")
        return (self.mode_append, [b"x"])

    def logout(self):
        self.appels.append(("logout",))

    def __getattr__(self, nom):
        raise AssertionError(f"méthode IMAP interdite : {nom}")

    def de_type(self, nom):
        return [a for a in self.appels if a[0] == nom]


def _creer(imap, sujet="Sujet é", corps="Corps accentué : à é ç", a=""):
    creer_brouillon(USER, MDP, sujet, corps, a, imap_factory=lambda: imap)


def test_un_seul_append_dans_le_dossier_des_brouillons_en_francais():
    imap = FauxImap()
    _creer(imap)
    ((_, boite, drapeaux, brut),) = imap.de_type("append")
    assert boite == "[Gmail]/Brouillons" and drapeaux == "(\\Draft)"
    message = email.message_from_bytes(brut, policy=email.policy.default)
    assert message["Subject"] == "Sujet é"
    assert message.get_content().strip() == "Corps accentué : à é ç"
    assert imap.de_type("logout") and [a[0] for a in imap.appels] == ["login", "list", "append", "logout"]


def test_dossier_repere_par_son_attribut_et_non_par_son_nom():
    imap = FauxImap([b'(\\HasNoChildren \\Drafts) "/" "[Gmail]/Drafts"', b'(\\HasNoChildren) "/" "INBOX"'])
    _creer(imap)
    assert imap.de_type("append")[0][1] == "[Gmail]/Drafts"


def test_dossier_nomme_brouillons_sans_attribut_n_est_pas_utilise():
    imap = FauxImap([b'(\\HasNoChildren) "/" "[Gmail]/Brouillons"'])
    with pytest.raises(ErreurGmail):
        _creer(imap)
    assert imap.de_type("append") == []


def test_aucun_destinataire_invente():
    imap = FauxImap()
    _creer(imap)
    message = email.message_from_bytes(imap.de_type("append")[0][3], policy=email.policy.default)
    assert message["To"] is None


def test_destinataire_fourni():
    imap = FauxImap()
    _creer(imap, a="rh@exemple.fr")
    message = email.message_from_bytes(imap.de_type("append")[0][3], policy=email.policy.default)
    assert message["To"] == "rh@exemple.fr"


def test_dossier_introuvable_sans_append_et_connexion_fermee():
    imap = FauxImap([b'(\\HasNoChildren) "/" "INBOX"'])
    with pytest.raises(ErreurGmail):
        _creer(imap)
    assert imap.de_type("append") == [] and imap.de_type("logout")


def test_liste_refusee():
    imap = FauxImap(liste="NO")
    with pytest.raises(ErreurGmail):
        _creer(imap)
    assert imap.de_type("append") == [] and imap.de_type("logout")


def test_connexion_refusee_sans_secret_dans_l_erreur():
    imap = FauxImap(login="refus")
    with pytest.raises(ErreurGmail) as e:
        _creer(imap)
    assert (
        USER not in str(e.value)
        and MDP not in str(e.value)
        and (e.value.__context__ is None or e.value.__suppress_context__)
    )
    assert imap.de_type("append") == [] and imap.de_type("logout")


@pytest.mark.parametrize("mode", ["NO", "BAD", "erreur"])
def test_append_refuse_sans_secret_dans_l_erreur(mode):
    imap = FauxImap(append=mode)
    with pytest.raises(ErreurGmail) as e:
        _creer(imap)
    assert (
        USER not in str(e.value)
        and MDP not in str(e.value)
        and (e.value.__context__ is None or e.value.__suppress_context__)
    )
    assert imap.de_type("logout")


def test_sujet_sur_une_ligne_pas_d_injection_d_en_tete():
    imap = FauxImap()
    _creer(imap, sujet="Dev\r\nBcc: autre@exemple.fr")
    message = email.message_from_bytes(imap.de_type("append")[0][3], policy=email.policy.default)
    assert message["Bcc"] is None and "\n" not in message["Subject"]


# --- texte déposé ---
def test_corps_pour_gmail_retire_la_ligne_de_profil_et_la_note():
    texte = "Madame, Monsieur,\n\nCorps.\n\n⚠️ longueur hors plage\nÉléments du profil utilisés : RiftMind"
    assert corps_pour_gmail(texte) == "Madame, Monsieur,\n\nCorps."


def _offre(titre="Développeur web"):
    return Offre(
        source="t", source_id="1", url="u", titre=titre, entreprise="ACME", commune="Paris", lat=None,
        lon=None, piste=Piste.ALTERNANCE, duree_mois=None, debut=None, niveau_diplome=None,
        description="d", publiee_le=None, expire_le=None,
    )  # fmt: skip


def test_sujets():
    assert sujet_brouillon("email", _offre()) == "Candidature : Développeur web"
    assert sujet_brouillon("relance", _offre()) == "Relance : candidature Développeur web"


def test_sujet_sur_une_ligne():
    assert "\n" not in sujet_brouillon("email", _offre("Dev\r\nweb"))


# --- invariant : jamais d'envoi ---
def test_aucun_module_n_importe_smtplib():
    fautifs = []
    for chemin in SRC.rglob("*.py"):
        for noeud in ast.walk(ast.parse(chemin.read_text(encoding="utf-8"))):
            noms = []
            if isinstance(noeud, ast.Import):
                noms = [a.name for a in noeud.names]
            elif isinstance(noeud, ast.ImportFrom):
                noms = [noeud.module or ""]
            if any(n.split(".")[0] == "smtplib" for n in noms):
                fautifs.append(chemin.name)
    assert fautifs == []


# --- pièces jointes ---
def _message_depose(imap):
    return email.message_from_bytes(imap.de_type("append")[0][3], policy=email.policy.default)


def test_pdf_en_piece_jointe_un_seul_append_et_octets_intacts():
    imap = FauxImap()
    pdf = b"%PDF-1.4\n\x00\xff\xfe binaire"
    creer_brouillon(
        USER, MDP, "Sujet", "Corps é", imap_factory=lambda: imap,
        pieces=[Piece("Lettre de motivation ACME.pdf", "application/pdf", pdf)],
    )  # fmt: skip
    assert len(imap.de_type("append")) == 1
    message = _message_depose(imap)
    (piece,) = list(message.iter_attachments())
    assert piece.get_content_type() == "application/pdf"
    assert piece.get_filename() == "Lettre de motivation ACME.pdf"
    assert piece.get_content() == pdf
    assert message.get_body().get_content().strip() == "Corps é"


def test_sans_piece_jointe_aucune_piece():
    imap = FauxImap()
    _creer(imap)
    assert list(_message_depose(imap).iter_attachments()) == []


def test_nom_de_piece_jointe_sur_une_ligne():
    imap = FauxImap()
    creer_brouillon(
        USER, MDP, "S", "C", imap_factory=lambda: imap,
        pieces=[Piece("a\r\nBcc: x@exemple.fr.pdf", "application/pdf", b"x")],
    )  # fmt: skip
    message = _message_depose(imap)
    assert message["Bcc"] is None and "\n" not in list(message.iter_attachments())[0].get_filename()


def test_type_mime_invalide_refuse_sans_append():
    imap = FauxImap()
    with pytest.raises(ErreurGmail):
        creer_brouillon(
            USER, MDP, "S", "C", imap_factory=lambda: imap,
            pieces=[Piece("a.pdf", "pas-un-type", b"x")],
        )  # fmt: skip
    assert imap.de_type("append") == []
