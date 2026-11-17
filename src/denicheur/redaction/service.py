"""Rédaction d'un brouillon avec le modèle d'écriture : longueur contrôlée en code, rien d'envoyé."""

import logging
import re
import time
from collections.abc import Callable
from pathlib import Path

import httpx

from denicheur.config import LLMConfig
from denicheur.models import Offre, ScoreLLM
from denicheur.redaction.prompts import (
    LIGNE_PROFIL,
    PLAGES,
    PROFILE,
    TYPES,
    message_systeme,
    message_utilisateur,
)
from denicheur.scoring.llm import OllamaIndisponible

__all__ = ["Redacteur", "RedactionInvalide"]

log = logging.getLogger(__name__)
SANS_LIGNE_PROFIL = f"{LIGNE_PROFIL} : non listés par le modèle, vérification impossible."
_INTRO = re.compile(r"Voici .{0,120}:")
# Un texte prêt à envoyer n'a aucun trou : « [à compléter : … ] » est retiré s'il échappe au modèle.
_A_COMPLETER = re.compile(r"\s*\[[^\]]*compl[ée]ter[^\]]*\]", re.IGNORECASE)
SECOND_ESSAI_MAX_S = 45  # au-delà, un second essai ferait attendre l'utilisateur plus de 90 s


class RedactionInvalide(Exception):
    """Réponse inutilisable (erreur HTTP, délai dépassé, JSON ou texte vide) ; sans détail interne."""


def _sans_trou(texte: str) -> str:
    return _A_COMPLETER.sub("", texte).strip()


def _separer(brut: str) -> tuple[str, str | None]:
    """(corps, ligne de profil) ; ce qui suit la ligne de profil est écarté."""
    lignes = brut.strip().splitlines()
    if lignes and _INTRO.fullmatch(lignes[0].strip()):  # « Voici le texte : » : bavardage du modèle
        lignes = lignes[1:]
    for i in range(len(lignes) - 1, -1, -1):
        if lignes[i].strip().startswith(LIGNE_PROFIL):
            return _sans_trou("\n".join(lignes[:i])), lignes[i].strip()
    return _sans_trou("\n".join(lignes)), None


def _ecart(corps: str, plage: tuple[int, int]) -> int:
    n = len(corps.split())
    return max(plage[0] - n, n - plage[1], 0)


class Redacteur:
    def __init__(
        self,
        llm: LLMConfig,
        http: httpx.Client,
        dossier: Path = PROFILE,
        horloge: Callable[[], float] = time.monotonic,
    ) -> None:
        self.llm, self.http, self.dossier, self.horloge = llm, http, dossier, horloge

    def _essai(self, systeme: str, utilisateur: str) -> tuple[str, str | None, float]:
        """(corps, ligne de profil, durée de l'appel en secondes)."""
        c = self.llm.ecriture  # modèle et options viennent de la config, jamais surchargés ici
        body = {
            "model": c.modele,
            "messages": [
                {"role": "system", "content": systeme},
                {"role": "user", "content": utilisateur},
            ],
            "stream": False,
            "keep_alive": "10m",
            "options": {"temperature": c.temperature, "num_ctx": c.num_ctx},
        }
        debut = self.horloge()
        try:
            r = self.http.post(f"{self.llm.url}/api/chat", json=body, timeout=c.timeout_s)
            r.raise_for_status()
            contenu = r.json()["message"]["content"]
        except httpx.ConnectError as e:
            raise OllamaIndisponible(str(e)) from e
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as e:
            raise RedactionInvalide(type(e).__name__) from e
        if not isinstance(contenu, str) or not contenu.strip():
            raise RedactionInvalide("réponse vide")
        corps, ligne = _separer(contenu)
        return corps, ligne, self.horloge() - debut

    def rediger(self, offre: Offre, score: ScoreLLM, type_: str) -> str:
        if type_ not in TYPES:
            raise ValueError(f"Type de brouillon inconnu : {type_}")
        systeme = message_systeme(self.dossier)  # lève avant tout appel si un fichier manque
        utilisateur = message_utilisateur(offre, score, type_)
        plage = PLAGES[type_]

        corps, ligne, duree = self._essai(systeme, utilisateur)
        if _ecart(corps, plage) and duree < SECOND_ESSAI_MAX_S:
            rappel = (
                f"\n\nTon texte précédent faisait {len(corps.split())} mots : refais-le avec "
                f"{plage[0]} à {plage[1]} mots, la ligne « {LIGNE_PROFIL} » exclue."
            )
            corps2, ligne2, _ = self._essai(systeme, utilisateur + rappel)
            if _ecart(corps2, plage) <= _ecart(corps, plage):
                corps, ligne = corps2, ligne2
        if _ecart(corps, plage):  # le texte part tel quel : la longueur n'est signalée que dans le journal
            log.info("rédaction %s hors plage : %d mots (%d à %d)", type_, len(corps.split()), *plage)
        return corps + "\n\n" + (ligne or SANS_LIGNE_PROFIL)
