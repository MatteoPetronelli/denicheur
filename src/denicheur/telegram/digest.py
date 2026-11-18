from datetime import date, datetime

from sqlalchemy.orm import Session

from denicheur.clock import paris_now
from denicheur.config import Config
from denicheur.db import repo
from denicheur.messages_fr import (
    RIEN_DE_NEUF,
    entete_digest,
    entete_entreprises,
    format_entreprise,
    format_offre,
)
from denicheur.models import Offre, Piste, ScoreLLM
from denicheur.telegram.api import TelegramAPI
from denicheur.telegram.keyboard import clavier_entreprise, clavier_offre


def envoyer_digest(session: Session, api: TelegramAPI, config: Config, now: datetime) -> int:
    """Envoie le top des offres non notifiées ; chaque offre est marquée dès son envoi."""
    a_envoyer = repo.offres_a_notifier(session, config.score_min, config.digest_max_offres)
    if not a_envoyer:
        api.send_message(RIEN_DE_NEUF)
        return 0
    api.send_message(entete_digest(len(a_envoyer)))
    for offre_id, offre, score in a_envoyer:
        api.send_message(format_offre(offre, score), clavier_offre(offre_id))
        repo.marquer_notifiee(session, offre_id, now)
        session.commit()  # un échec en cours de route ne renvoie pas ce qui est déjà parti
    return len(a_envoyer)


def envoyer_liste_entreprises(session: Session, api: TelegramAPI, config: Config, now: datetime) -> int:
    """Envoie les entreprises du jour, une par message ; chacune est marquée listée dès son envoi.

    Le quota du jour tient compte de celles déjà listées (reprise après un échec) : jamais plus de
    `liste_par_jour` par jour Paris, jamais deux fois la même.
    """
    restant = config.entreprises.liste_par_jour - repo.nb_listees_le(session, paris_now(now).date())
    a_envoyer = repo.entreprises_du_jour(session, restant)
    if not a_envoyer:
        return 0
    api.send_message(entete_entreprises(len(a_envoyer)))
    for entreprise_id, entreprise in a_envoyer:
        offres = repo.titres_offres_du_siret(session, entreprise.siret)
        api.send_message(format_entreprise(entreprise, offres), clavier_entreprise(entreprise_id))
        repo.marquer_listee(session, entreprise_id, now)
        session.commit()  # un échec en cours de route ne renvoie pas ce qui est déjà parti
    return len(a_envoyer)


def envoyer_test(api: TelegramAPI) -> None:
    offre = Offre(
        source="test", source_id="0", url="https://example.org", titre="[TEST] Offre factice",
        entreprise="Exemple SAS", commune="Paris", lat=None, lon=None, piste=Piste.ALTERNANCE,
        duree_mois=12, debut=date(2027, 1, 1), niveau_diplome=None, description="",
        publiee_le=None, expire_le=None, distance_km=6.0,
    )  # fmt: skip
    score = ScoreLLM(
        score=86, type="alternance", points_forts=["React", "Python"], points_faibles=[],
        alerte=None, projet_a_citer="RiftMind", resume="Message de test.",
    )  # fmt: skip
    api.send_message(format_offre(offre, score))
