import pytest

from denicheur.telegram.keyboard import (
    clavier_brouillon,
    clavier_depose,
    clavier_envoyee,
    clavier_offre,
    clavier_rappel,
    lire_donnee,
)


def test_clavier_offre_cinq_boutons_pour_la_meme_offre():
    boutons = [b for ligne in clavier_offre(42)["inline_keyboard"] for b in ligne]
    assert [b["callback_data"] for b in boutons] == ["p:42", "b:42", "r:42", "x:42", "d:42"]
    assert [b["text"] for b in boutons] == [
        "✅ Je postule", "✍️ Brouillon", "⏰ Rappel", "🚫 Ignorer", "📄 Lettre PDF",
    ]  # fmt: skip


def test_donnee_de_bouton_tient_dans_64_octets_meme_pour_un_grand_id():
    for b in (b for ligne in clavier_offre(999_999_999)["inline_keyboard"] for b in ligne):
        assert len(b["callback_data"].encode()) <= 64


def test_clavier_envoyee_est_un_seul_bouton_inerte():
    (bouton,) = [b for ligne in clavier_envoyee()["inline_keyboard"] for b in ligne]
    assert bouton["text"] == "✅ Envoyée"
    assert lire_donnee(bouton["callback_data"]) is None


@pytest.mark.parametrize(("donnee", "attendu"), [("p:7", ("p", 7)), ("x:123456789", ("x", 123456789))])
def test_lire_donnee_valide(donnee, attendu):
    assert lire_donnee(donnee) == attendu


@pytest.mark.parametrize(
    "donnee", ["zzz", "", "p:", "p:abc", "z:1", "p:1 ", "p:-1", "p:1234567890", "p:٣", "P:1", "p:1:2", None]
)
def test_lire_donnee_invalide(donnee):
    assert lire_donnee(donnee) is None


def test_clavier_brouillon_un_bouton_gmail_qui_porte_l_id_du_brouillon():
    (bouton,) = [b for ligne in clavier_brouillon(7)["inline_keyboard"] for b in ligne]
    assert bouton == {"text": "📥 Créer le brouillon Gmail", "callback_data": "g:7"}


def test_clavier_depose_est_inerte():
    (bouton,) = [b for ligne in clavier_depose()["inline_keyboard"] for b in ligne]
    assert bouton["text"] == "✅ Brouillon Gmail créé"
    assert lire_donnee(bouton["callback_data"]) is None


def test_clavier_rappel_un_bouton_relance_qui_porte_l_id_de_l_offre():
    (bouton,) = [b for ligne in clavier_rappel(42)["inline_keyboard"] for b in ligne]
    assert bouton == {"text": "✉️ Relance", "callback_data": "l:42"}


def test_donnees_g_et_l_longues_tiennent_dans_64_octets():
    for clavier in (clavier_brouillon(999_999_999), clavier_rappel(999_999_999)):
        for b in (b for ligne in clavier["inline_keyboard"] for b in ligne):
            assert len(b["callback_data"].encode()) <= 64


@pytest.mark.parametrize(
    ("donnee", "attendu"), [("g:12", ("g", 12)), ("l:3", ("l", 3)), ("d:9", ("d", 9)), ("p:1", ("p", 1))]
)
def test_lire_donnee_accepte_g_et_l(donnee, attendu):
    assert lire_donnee(donnee) == attendu


@pytest.mark.parametrize(
    "donnee", ["g:abc", "l:", "z:1", "gl:1", "g:1:2", "g:-1", "g:1234567890", "G:1", " g:1"]
)
def test_lire_donnee_refuse_le_reste(donnee):
    assert lire_donnee(donnee) is None
