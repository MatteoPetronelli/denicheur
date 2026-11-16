"""Clavier en ligne des offres et lecture stricte de la donnée d'un bouton (≤ 64 octets)."""

import re
from typing import Any

_DONNEE = re.compile(r"[pbrx]:[0-9]{1,9}")


def clavier_offre(offre_id: int) -> dict[str, Any]:
    def bouton(texte: str, action: str) -> dict[str, str]:
        return {"text": texte, "callback_data": f"{action}:{offre_id}"}

    return {
        "inline_keyboard": [
            [bouton("✅ Je postule", "p"), bouton("✍️ Brouillon", "b")],
            [bouton("⏰ Rappel", "r"), bouton("🚫 Ignorer", "x")],
        ]
    }


def clavier_envoyee() -> dict[str, Any]:
    return {"inline_keyboard": [[{"text": "✅ Envoyée", "callback_data": "noop"}]]}


def lire_donnee(donnee: object) -> tuple[str, int] | None:
    """(action, offre_id), ou None si la donnée n'a pas exactement la forme attendue."""
    if not isinstance(donnee, str) or not _DONNEE.fullmatch(donnee):
        return None
    action, _, ident = donnee.partition(":")
    return action, int(ident)
