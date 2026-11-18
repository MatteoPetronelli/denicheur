"""Actualisation quotidienne des entreprises : recruteurs de La bonne alternance puis recherche publique."""

import time
from collections.abc import Callable
from datetime import datetime
from typing import Any

import httpx
from sqlalchemy.orm import Session

from denicheur.config import Config
from denicheur.db import repo
from denicheur.entreprises import recherche
from denicheur.entreprises.lba import depuis_recruteurs


def actualiser_entreprises(
    session: Session, config: Config, now: datetime,
    recruteurs: Callable[[], list[dict[str, Any]]] | None, http_publique: httpx.Client,
    sleep: Callable[[float], None] = time.sleep,
) -> list[str]:  # fmt: skip
    """Renvoie les erreurs consignées ; une source en panne n'empêche pas l'autre.

    `http_publique` est un client sans en-tête d'authentification : la clé LBA ne doit jamais partir vers
    l'API publique.
    """
    erreurs: list[str] = []
    if recruteurs is not None:
        try:
            retenues, _ = depuis_recruteurs(recruteurs(), config)
            for entreprise in retenues:
                repo.enregistrer_entreprise(session, entreprise, now)
            session.commit()
        except Exception as e:  # noqa: BLE001 : toute panne de LBA est isolée, seul le type est consigné
            session.rollback()
            erreurs.append(f"entreprises lba : {type(e).__name__}")
    erreurs += recherche.actualiser(session, config, http_publique, now, sleep).erreurs
    return erreurs
