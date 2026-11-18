"""Clavier en ligne des offres et lecture stricte de la donnée d'un bouton (≤ 64 octets)."""

import re
from typing import Any

# p b r x d l : offre ; s t e i : entreprise ; g : brouillon
_DONNEE = re.compile(r"[pbrxgldstie]:[0-9]{1,9}")


def clavier_offre(offre_id: int) -> dict[str, Any]:
    def bouton(texte: str, action: str) -> dict[str, str]:
        return {"text": texte, "callback_data": f"{action}:{offre_id}"}

    return {
        "inline_keyboard": [
            [bouton("✅ Je postule", "p"), bouton("✍️ Brouillon", "b")],
            [bouton("⏰ Rappel", "r"), bouton("🚫 Ignorer", "x")],
            [bouton("📄 Lettre PDF", "d")],
        ]
    }


def clavier_entreprise(entreprise_id: int) -> dict[str, Any]:
    def bouton(texte: str, action: str) -> dict[str, str]:
        return {"text": texte, "callback_data": f"{action}:{entreprise_id}"}

    return {
        "inline_keyboard": [
            [bouton("✉️ Brouillon spontané", "s"), bouton("📄 Lettre PDF", "t")],
            [bouton("✅ Envoyée", "e"), bouton("❌ Ignorer", "i")],
        ]
    }


def _un_bouton(texte: str, donnee: str) -> dict[str, Any]:
    return {"inline_keyboard": [[{"text": texte, "callback_data": donnee}]]}


def clavier_brouillon(brouillon_id: int) -> dict[str, Any]:
    return _un_bouton("📥 Créer le brouillon Gmail", f"g:{brouillon_id}")


def clavier_depose() -> dict[str, Any]:
    return _un_bouton("✅ Brouillon Gmail créé", "noop")


def clavier_rappel(offre_id: int) -> dict[str, Any]:
    return _un_bouton("✉️ Relance", f"l:{offre_id}")


def clavier_envoyee() -> dict[str, Any]:
    return {"inline_keyboard": [[{"text": "✅ Envoyée", "callback_data": "noop"}]]}


def lire_donnee(donnee: object) -> tuple[str, int] | None:
    """(action, offre_id), ou None si la donnée n'a pas exactement la forme attendue."""
    if not isinstance(donnee, str) or not _DONNEE.fullmatch(donnee):
        return None
    action, _, ident = donnee.partition(":")
    return action, int(ident)
