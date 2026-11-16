"""Déductions sur le texte d'une offre, communes aux sources qui n'ont pas de champ structuré."""

import re
import unicodedata

from denicheur.models import Piste

_ALTERNANCE = ("alternance", "apprentissage", "apprenti", "alternant")
_STAGE = ("stage", "stagiaire", "internship")
_TELETRAVAIL = re.compile(r"t[ée]l[ée]travail|hybride|remote", re.IGNORECASE)


def _sans_accent(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def piste_dans(texte: str, *, stage_d_abord: bool = False) -> Piste | None:
    """Piste annoncée par un texte, ou None s'il n'en dit rien. Le premier mot-clé testé l'emporte."""
    t = _sans_accent(texte)
    tests = [(Piste.ALTERNANCE, _ALTERNANCE), (Piste.STAGE, _STAGE)]
    for piste, mots in tests[::-1] if stage_d_abord else tests:
        if any(m in t for m in mots):
            return piste
    return None


def est_teletravail(texte: str) -> bool:
    return _TELETRAVAIL.search(texte) is not None
