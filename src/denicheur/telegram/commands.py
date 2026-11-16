"""Commandes Telegram : texte reçu -> réponses (texte + clavier éventuel). Aucun envoi ici."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from denicheur.clock import paris_now
from denicheur.config import Config
from denicheur.db import repo
from denicheur.messages_fr import (
    AIDE,
    AUCUNE_CANDIDATURE,
    AUCUNE_RELANCE,
    PAUSE_ACTIVEE,
    PAUSE_LEVEE,
    RIEN_DE_NEUF,
    format_offre,
    liste_suivi,
    texte_config,
    texte_stats,
)
from denicheur.models import Offre, Piste, ScoreLLM
from denicheur.telegram.keyboard import clavier_offre

MAX_OFFRES = 5
MAX_SUIVI = 20


@dataclass
class Reponse:
    texte: str
    clavier: dict[str, Any] | None = None


def _offres(trouvees: list[tuple[int, Offre, ScoreLLM]]) -> list[Reponse]:
    if not trouvees:
        return [Reponse(RIEN_DE_NEUF)]
    return [Reponse(format_offre(o, s), clavier_offre(oid)) for oid, o, s in trouvees]


def repondre(texte: str, session: Session, config: Config, now: datetime) -> list[Reponse]:
    mots = texte.strip().split()
    commande = mots[0].split("@")[0].lower() if mots else ""
    today = paris_now(now).date()
    match commande:
        case "/aujourdhui":
            return _offres(repo.offres_du_jour(session, today)[:MAX_OFFRES])
        case "/stage":
            return _offres(repo.meilleures_offres(session, Piste.STAGE, MAX_OFFRES))
        case "/alternance":
            return _offres(repo.meilleures_offres(session, Piste.ALTERNANCE, MAX_OFFRES))
        case "/candidatures":
            suivi = repo.suivi_en_cours(session, MAX_SUIVI)
            if not suivi:
                return [Reponse(AUCUNE_CANDIDATURE)]
            return [Reponse(liste_suivi("Candidatures", [(o, s) for _, o, s in suivi]))]
        case "/relances":
            dues = repo.candidatures_a_relancer(session, today)
            if not dues:
                return [Reponse(AUCUNE_RELANCE)]
            return [Reponse(liste_suivi("À relancer", [(o, None) for _, o in dues]))]
        case "/stats":
            return [Reponse(texte_stats(repo.stats(session)))]
        case "/pause" | "/reprendre":
            pause = commande == "/pause"
            repo.set_param(session, "pause", "1" if pause else "0")
            session.commit()
            return [Reponse(PAUSE_ACTIVEE if pause else PAUSE_LEVEE)]
        case "/config":
            return [Reponse(texte_config(config, repo.get_param(session, "pause") == "1"))]
        case _:
            return [Reponse(AIDE)]
