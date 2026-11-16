import pytest

from denicheur.telegram.keyboard import clavier_envoyee, clavier_offre, lire_donnee


def test_clavier_offre_quatre_boutons_pour_la_meme_offre():
    boutons = [b for ligne in clavier_offre(42)["inline_keyboard"] for b in ligne]
    assert [b["callback_data"] for b in boutons] == ["p:42", "b:42", "r:42", "x:42"]
    assert [b["text"] for b in boutons] == ["✅ Je postule", "✍️ Brouillon", "⏰ Rappel", "🚫 Ignorer"]


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
