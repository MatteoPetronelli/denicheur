import contextlib
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.orm import Session

from denicheur.clock import heure_atteinte, is_daytime, paris_now
from denicheur.config import Config
from denicheur.db import repo
from denicheur.messages_fr import echec_collecte, format_offre
from denicheur.models import Offre, Piste
from denicheur.pipeline.dedupe import cle_dedup, dedupliquer
from denicheur.pipeline.geo import appliquer_geo
from denicheur.pipeline.prefilter import prefiltrer
from denicheur.scoring.llm import Scorer
from denicheur.scoring.service import scorer_offres
from denicheur.telegram.api import TelegramAPI, TelegramError
from denicheur.telegram.digest import envoyer_digest

MODES = ("auto", "alternance", "stage", "digest")
Source = Callable[[Config, datetime], list[Offre]]


@dataclass
class Deps:
    session: Session
    config: Config
    sources: dict[str, Source]  # sources alternance ; les stages arrivent avec C3
    scorer: Scorer
    api: TelegramAPI | None = None  # None : aucun envoi (--dry-run)
    chrono: Callable[[], float] = time.monotonic


@dataclass
class Bilan:
    ok: bool = True
    collectees: int = 0
    retenues: int = 0
    scorees: int = 0
    notifiees: int = 0
    erreurs: list[str] = field(default_factory=list)


def _alternance_due(deps: Deps, mode: str, now: datetime) -> bool:
    if mode == "alternance":
        return True
    if mode != "auto" or not is_daytime(now, *deps.config.plage_alertes):
        return False
    derniere = repo.get_param(deps.session, "derniere_collecte:alternance")
    if derniere is None:
        return True
    ecart = now.timestamp() - datetime.fromisoformat(derniere).timestamp()
    return ecart >= deps.config.pistes.alternance.frequence_heures * 3600


def _collecter(deps: Deps, mode: str, now: datetime, bilan: Bilan) -> None:
    if not _alternance_due(deps, mode, now):
        return
    s = deps.session
    brutes: list[Offre] = []
    for nom, source in deps.sources.items():
        try:
            brutes += source(deps.config, now)
        except Exception as e:  # une source en panne ne bloque pas le run
            bilan.erreurs.append(f"source {nom} : {type(e).__name__}")
    repo.set_param(s, "derniere_collecte:alternance", now.isoformat())
    bilan.collectees = len(brutes)
    nouvelles = dedupliquer(brutes, repo.urls_connues(s), repo.cles_connues(s))
    nouvelles = prefiltrer(appliquer_geo(nouvelles, deps.config), deps.config, now)
    for o in nouvelles:
        repo.inserer_offre(s, o, cle_dedup=cle_dedup(o), now=now)
    bilan.retenues = sum(o.motif_rejet is None for o in nouvelles)
    s.commit()


def _notifier(deps: Deps, mode: str, now: datetime) -> int:
    api, s, cfg = deps.api, deps.session, deps.config
    if api is None or repo.get_param(s, "pause") == "1":
        return 0
    envoyees = 0
    if is_daytime(now, *cfg.plage_alertes):
        for offre_id, offre, score in repo.offres_a_notifier(s, cfg.alerte_immediate_alternance_min, 100):
            if offre.piste is Piste.ALTERNANCE:
                api.send_message(format_offre(offre, score, alerte=True))
                repo.marquer_notifiee(s, offre_id, now)
                s.commit()
                envoyees += 1
    aujourdhui = paris_now(now).date().isoformat()
    attendu = mode == "digest" or (mode == "auto" and heure_atteinte(now, cfg.heure_digest))
    if attendu and repo.get_param(s, "dernier_digest") != aujourdhui:
        envoyees += envoyer_digest(s, api, cfg, now)
        repo.set_param(s, "dernier_digest", aujourdhui)
        s.commit()
    return envoyees


def executer(mode: str, deps: Deps, now: datetime) -> Bilan:
    s = deps.session
    bilan = Bilan()
    execution_id = repo.ouvrir_execution(s, mode, now)
    s.commit()
    llm_s = 0.0
    try:
        _collecter(deps, mode, now, bilan)
        debut_llm = deps.chrono()
        bilan.scorees = scorer_offres(
            s, repo.offres_sans_score(s), deps.config, deps.scorer, now, erreurs=bilan.erreurs,
            chrono=deps.chrono,
        )  # fmt: skip
        llm_s = deps.chrono() - debut_llm
        bilan.notifiees = _notifier(deps, mode, now)
    except Exception as e:  # dernier filet : on consigne, on prévient sans détail, code de sortie 1
        s.rollback()
        bilan.ok = False
        bilan.erreurs.append(f"échec : {type(e).__name__}")
        if deps.api is not None:
            with contextlib.suppress(TelegramError):
                deps.api.send_message(echec_collecte(type(e).__name__))
    repo.clore_execution(
        s, execution_id, now, offres_collectees=bilan.collectees, offres_retenues=bilan.retenues,
        offres_scorees=bilan.scorees, offres_notifiees=bilan.notifiees, erreurs=bilan.erreurs,
        duree_llm_s=llm_s,
    )  # fmt: skip
    s.commit()
    return bilan
