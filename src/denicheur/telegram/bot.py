"""Bot Telegram en long polling : liste blanche du chat, une seule prise en compte par update."""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from denicheur import messages_fr as fr
from denicheur.config import Config
from denicheur.db import repo
from denicheur.models import Statut
from denicheur.telegram.api import TelegramAPI, TelegramError
from denicheur.telegram.commands import repondre
from denicheur.telegram.keyboard import clavier_envoyee, lire_donnee

log = logging.getLogger(__name__)
ATTENTE_ERREUR_S = 5
LONG_POLLING_S = 50
CLE_OFFSET = "dernier_update_id"
# action du bouton -> (statut visé, réponse, réponse si déjà fait)
_ACTIONS = {
    "p": (Statut.CANDIDATURE_ENVOYEE, fr.CB_ENVOYEE, fr.CB_DEJA_ENVOYEE),
    "r": (Statut.INTERESSANTE, fr.CB_GARDEE, fr.CB_DEJA_GARDEE),
    "x": (Statut.IGNOREE, fr.CB_IGNOREE, fr.CB_DEJA_IGNOREE),
}


@dataclass
class BotDeps:
    api: TelegramAPI
    session: Session
    config: Config
    chat_id: str
    maintenant: Callable[[], datetime]


def _bouton(deps: BotDeps, cq: dict[str, Any]) -> None:
    api, session = deps.api, deps.session
    # Le chat et l'auteur doivent être les nôtres : un bouton transféré vers un autre compte ne compte pas.
    if str(cq["message"]["chat"]["id"]) != deps.chat_id or str(cq["from"]["id"]) != deps.chat_id:
        return
    lu = lire_donnee(cq.get("data"))
    if lu is None:
        api.answer_callback(cq["id"], fr.CB_INCONNU)
        return
    action, offre_id = lu
    if action == "b":
        api.answer_callback(cq["id"], fr.CB_BROUILLON)
        return
    statut, fait, deja = _ACTIONS[action]
    try:
        courant = repo.statut_de(session, offre_id)
        if courant is statut:
            api.answer_callback(cq["id"], deja)
            return
        repo.marquer(session, offre_id, statut, deps.maintenant())
        session.commit()
    except repo.OffreInconnue:
        api.answer_callback(cq["id"], fr.CB_INTROUVABLE)
        return
    except repo.TransitionInvalide:
        api.answer_callback(cq["id"], fr.cb_impossible(courant.value if courant else None))
        return
    api.answer_callback(cq["id"], fait)
    if statut is Statut.CANDIDATURE_ENVOYEE:
        api.edit_keyboard(cq["message"]["message_id"], clavier_envoyee())


def _message(deps: BotDeps, message: dict[str, Any]) -> None:
    if str(message["chat"]["id"]) != deps.chat_id:
        return
    for r in repondre(message.get("text") or "", deps.session, deps.config, deps.maintenant()):
        deps.api.send_message(r.texte, r.clavier)


def _traiter(deps: BotDeps, update: dict[str, Any]) -> None:
    if "callback_query" in update:
        _bouton(deps, update["callback_query"])
    elif "message" in update:
        _message(deps, update["message"])


def boucle(
    deps: BotDeps,
    *,
    sleep: Callable[[float], None] = time.sleep,
    continuer: Callable[[], bool] = lambda: True,
) -> None:
    """Ne s'arrête jamais d'elle-même ; `continuer` ne sert qu'aux tests."""
    try:
        deps.api.delete_webhook()
    except TelegramError as e:
        log.warning("deleteWebhook : %s", e)
    dernier = int(repo.get_param(deps.session, CLE_OFFSET) or 0)
    while continuer():
        try:
            updates = deps.api.get_updates(offset=dernier + 1 if dernier else None, timeout=LONG_POLLING_S)
        except TelegramError as e:
            log.warning("%s", e)
            sleep(ATTENTE_ERREUR_S)
            continue
        for update in updates:
            uid = update["update_id"]
            if uid <= dernier:
                continue
            try:
                _traiter(deps, update)
            except Exception as e:  # une update défectueuse ne doit pas bloquer la file
                deps.session.rollback()
                log.warning("update %s : %s", uid, type(e).__name__)
            repo.set_param(deps.session, CLE_OFFSET, str(uid))
            deps.session.commit()
            dernier = uid
