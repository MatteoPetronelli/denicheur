import time
from collections.abc import Callable
from datetime import datetime

from sqlalchemy.orm import Session

from denicheur.config import Config
from denicheur.db import repo
from denicheur.models import Offre
from denicheur.scoring.llm import OllamaIndisponible, ScoreInvalide, Scorer


def _cle_echecs(now: datetime) -> str:
    return f"echecs_llm:{now.astimezone(repo.PARIS).date().isoformat()}"


def scorer_offres(
    session: Session,
    offres: list[tuple[int, Offre]],
    config: Config,
    scorer: Scorer,
    now: datetime,
    *,
    erreurs: list[str] | None = None,
    chrono: Callable[[], float] = time.monotonic,
) -> int:
    """Note les offres (id, offre) sans score. Retourne le nombre de scores créés.

    S'arrête au plafond d'appels du jour (tentatives invalides comprises) ou à `llm_max_duree_run_s`.
    """
    llm = config.llm
    erreurs = erreurs if erreurs is not None else []
    cle = _cle_echecs(now)
    debut, crees = chrono(), 0
    for offre_id, offre in offres:
        if repo.lire_score(session, offre_id) is not None:
            continue
        echecs = int(repo.get_param(session, cle) or 0)
        if repo.appels_llm_aujourdhui(session, now) + echecs >= llm.llm_max_appels_jour:
            break
        if chrono() - debut >= llm.llm_max_duree_run_s:
            break
        try:
            score, usage = scorer.scorer(offre, now.astimezone(repo.PARIS).date())
        except OllamaIndisponible as e:
            erreurs.append(f"ollama indisponible : {e}")
            break
        except ScoreInvalide as e:
            repo.set_param(session, cle, str(echecs + 1))
            session.commit()
            erreurs.append(f"score invalide (offre {offre_id}) : {e}")
            continue
        repo.inserer_score(
            session, offre_id, score, modele=llm.scoring.modele, prompt_tokens=usage.prompt_tokens,
            output_tokens=usage.output_tokens, duree_s=usage.duree_s, now=now,
        )  # fmt: skip
        session.commit()
        crees += 1
    return crees
