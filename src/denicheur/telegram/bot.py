"""Bot Telegram en long polling : liste blanche du chat, une seule prise en compte par update."""

import logging
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from sqlalchemy.orm import Session

from denicheur import messages_fr as fr
from denicheur.clock import paris_now
from denicheur.config import Config
from denicheur.db import repo
from denicheur.models import Offre, ScoreLLM, Statut
from denicheur.redaction.documents import (
    IDENTITE,
    LIENS,
    ErreurDocuments,
    Identite,
    ecrire_lettre,
    lire_identite,
    lire_liens,
    nom_fichier,
    rendre_lettre,
)
from denicheur.redaction.gmail_drafts import ErreurGmail, Piece, corps_pour_gmail, sujet_brouillon
from denicheur.redaction.prompts import ProfilManquant
from denicheur.redaction.service import RedactionInvalide
from denicheur.scoring.llm import OllamaIndisponible
from denicheur.telegram.api import TelegramAPI, TelegramError
from denicheur.telegram.commands import repondre
from denicheur.telegram.keyboard import clavier_brouillon, clavier_depose, clavier_envoyee, lire_donnee

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


class Redacteur(Protocol):
    def rediger(self, offre: Offre, score: ScoreLLM, type_: str) -> str: ...


@dataclass
class BotDeps:
    api: TelegramAPI
    session: Session
    config: Config
    chat_id: str
    maintenant: Callable[[], datetime]
    redacteur: Redacteur | None = None
    deposer: Callable[[str, str, Sequence[Piece]], None] | None = None  # (sujet, corps, pièces) -> Gmail
    dossier_lettres: Path | None = None
    chemin_identite: Path = IDENTITE
    chemin_liens: Path = LIENS


PDF = "application/pdf"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _identite(deps: BotDeps, cq: dict[str, Any], *, dossier: bool) -> Identite | None:
    """L'identité locale (et le dossier si `dossier`) ; sinon répond et renvoie None, sans appel au modèle."""
    try:
        if dossier:
            if deps.dossier_lettres is None:
                deps.api.answer_callback(cq["id"], fr.CB_LETTRES_ABSENT)
                return None
            if not deps.dossier_lettres.is_dir():
                raise ErreurDocuments("Dossier des lettres introuvable")
        return lire_identite(deps.chemin_identite)
    except ErreurDocuments as e:  # messages sans chemin ni donnée personnelle
        deps.api.answer_callback(cq["id"], str(e))
        return None


def _rediger(deps: BotDeps, cq: dict[str, Any], offre_id: int, type_: str) -> None:
    """Génère, enregistre et envoie un brouillon ; la boucle bloque pendant l'appel au modèle."""
    api, session = deps.api, deps.session
    if deps.redacteur is None:
        api.answer_callback(cq["id"], fr.CB_REDACTION_ABSENTE)
        return
    try:
        repo.verifier_brouillon(session, offre_id, type_)  # avant l'appel au modèle : un refus ne coûte rien
    except repo.OffreInconnue:
        api.answer_callback(cq["id"], fr.CB_INTROUVABLE)
        return
    except repo.RelanceDejaFaite:
        api.answer_callback(cq["id"], fr.CB_RELANCE_DEJA)
        return
    except repo.TransitionInvalide:
        courant = repo.statut_de(session, offre_id)
        api.answer_callback(cq["id"], fr.cb_impossible(courant.value if courant else None))
        return
    score = repo.lire_score(session, offre_id)
    if score is None:
        api.answer_callback(cq["id"], fr.CB_SANS_SCORE)
        return
    identite = None
    if type_ == "lettre":
        identite = _identite(deps, cq, dossier=True)
        if identite is None:
            return
    api.answer_callback(cq["id"], fr.CB_ATTENTE)
    offre = repo.lire_offre(session, offre_id)
    debut = time.monotonic()
    try:
        texte = deps.redacteur.rediger(offre, score, type_)
    except OllamaIndisponible:
        log.warning("rédaction %s offre %s : Ollama indisponible", type_, offre_id)
        api.send_message(fr.ECHEC_OLLAMA)
        return
    except RedactionInvalide as e:  # str(e) = nom de l'erreur, jamais d'URL ni de texte
        log.warning("rédaction %s offre %s : %s après %.1f s", type_, offre_id, e, time.monotonic() - debut)
        api.send_message(fr.ECHEC_REDACTION)
        return
    except ProfilManquant as e:
        api.send_message(fr.echec_profil(str(e)))
        return
    log.info("rédaction %s offre %s : %.1f s", type_, offre_id, time.monotonic() - debut)
    fichiers: tuple[Path, Path] | None = None
    if identite is not None and deps.dossier_lettres is not None:
        try:  # avant l'enregistrement : un échec d'écriture ne laisse aucun brouillon
            fichiers = ecrire_lettre(
                texte,
                offre,
                identite,
                deps.dossier_lettres,
                paris_now(deps.maintenant()).date(),
                lire_liens(deps.chemin_liens),
            )
        except ErreurDocuments:
            api.send_message(fr.ECHEC_FICHIERS)
            return
    brouillon_id = repo.enregistrer_brouillon(session, offre_id, type_, texte, deps.maintenant())
    session.commit()
    if fichiers is None or identite is None:
        api.send_message(fr.texte_brouillon(type_, texte), clavier_brouillon(brouillon_id))
        return
    api.send_message(fr.texte_brouillon(type_, texte))  # le texte relu garde la ligne de vérification
    for chemin, mime in zip(fichiers, (PDF, DOCX), strict=True):
        api.send_document(chemin.name, chemin.read_bytes(), mime)
    api.send_message(
        fr.accompagnement_telegram(offre.titre, offre.entreprise, identite.nom),
        clavier_brouillon(brouillon_id),
    )


def _deposer(deps: BotDeps, cq: dict[str, Any], brouillon_id: int) -> None:
    api, session = deps.api, deps.session
    brouillon = repo.lire_brouillon(session, brouillon_id)
    if brouillon is None:
        api.answer_callback(cq["id"], fr.CB_INTROUVABLE)
        return
    if brouillon.depose:
        api.answer_callback(cq["id"], fr.CB_DEJA_DEPOSE)
        return
    if deps.deposer is None:
        api.answer_callback(cq["id"], fr.CB_GMAIL_ABSENT)
        return
    offre = repo.lire_offre(session, brouillon.offre_id)
    corps, pieces = corps_pour_gmail(brouillon.contenu), []
    if brouillon.type == "lettre":  # message fixe en corps, PDF régénéré en pièce jointe (rien n'est écrit)
        identite = _identite(deps, cq, dossier=False)
        if identite is None:
            return
        try:
            jour = paris_now(deps.maintenant()).date()
            pdf, _ = rendre_lettre(brouillon.contenu, offre, identite, jour, lire_liens(deps.chemin_liens))
        except ErreurDocuments:
            api.answer_callback(cq["id"], fr.CB_FICHIERS_ECHEC)
            return
        corps = fr.message_accompagnement(offre.titre, offre.entreprise, identite.nom)
        pieces = [Piece(f"{nom_fichier(offre.entreprise)}.pdf", PDF, pdf)]
    try:
        deps.deposer(sujet_brouillon(brouillon.type, offre), corps, pieces)
    except ErreurGmail:
        api.answer_callback(cq["id"], fr.CB_GMAIL_ECHEC)
        return
    repo.marquer_depose(session, brouillon_id)
    session.commit()
    api.answer_callback(cq["id"], fr.CB_DEPOSE)
    api.edit_keyboard(cq["message"]["message_id"], clavier_depose())


def _bouton_entreprise(deps: BotDeps, cq: dict[str, Any], action: str, entreprise_id: int) -> None:
    api, session = deps.api, deps.session
    if action in ("s", "t"):
        api.answer_callback(cq["id"], fr.CB_ENTREPRISE_BIENTOT)
        return
    statut, fait, deja = (
        (Statut.CANDIDATURE_ENVOYEE, fr.CB_ENVOYEE, fr.CB_DEJA_ENVOYEE)
        if action == "e"
        else (Statut.IGNOREE, fr.CB_ENTREPRISE_IGNOREE, fr.CB_DEJA_IGNOREE)
    )
    courant = repo.statut_de_entreprise(session, entreprise_id)
    if courant is statut:
        api.answer_callback(cq["id"], deja)
        return
    try:
        repo.marquer_entreprise(session, entreprise_id, statut, deps.maintenant())
        session.commit()
    except repo.EntrepriseInconnue:
        api.answer_callback(cq["id"], fr.CB_ENTREPRISE_INTROUVABLE)
        return
    except repo.TransitionInvalide:
        api.answer_callback(cq["id"], fr.cb_impossible_entreprise(courant.value if courant else None))
        return
    api.answer_callback(cq["id"], fait)
    if statut is Statut.CANDIDATURE_ENVOYEE:
        api.edit_keyboard(cq["message"]["message_id"], clavier_envoyee())


def _bouton(deps: BotDeps, cq: dict[str, Any]) -> None:
    api, session = deps.api, deps.session
    # Le chat et l'auteur doivent être les nôtres : un bouton transféré vers un autre compte ne compte pas.
    if str(cq["message"]["chat"]["id"]) != deps.chat_id or str(cq["from"]["id"]) != deps.chat_id:
        return
    lu = lire_donnee(cq.get("data"))
    if lu is None:
        api.answer_callback(cq["id"], fr.CB_INCONNU)
        return
    action, offre_id = lu  # pour s, t, e, i l'identifiant est celui d'une entreprise
    if action in ("s", "t", "e", "i"):
        _bouton_entreprise(deps, cq, action, offre_id)
        return
    if action in ("b", "l", "d"):
        _rediger(deps, cq, offre_id, {"b": "email", "l": "relance", "d": "lettre"}[action])
        return
    if action == "g":
        _deposer(deps, cq, offre_id)  # ici l'identifiant est celui d'un brouillon
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
