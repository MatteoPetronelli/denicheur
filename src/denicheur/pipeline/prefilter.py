import re
from datetime import datetime, timedelta

from denicheur.config import Config
from denicheur.models import Offre, Piste
from denicheur.pipeline.normalize import normaliser_texte as norm


def _mot(mot: str, texte: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(norm(mot))}(?!\w)", texte) is not None


def _motif(o: Offre, config: Config, now: datetime) -> str | None:
    titre = norm(o.titre)
    if o.piste is Piste.AUTRE:
        return "piste_autre"
    if o.expire_le and o.expire_le < now:
        return "expiree"
    if o.publiee_le and o.publiee_le < now - timedelta(days=config.age_max_jours):
        return "trop_ancienne"
    for mot in config.mots_exclus:
        if _mot(mot, titre):
            return f"mot_exclu:{norm(mot)}"
    if not any(_mot(m, titre) for m in config.mots_cles_titre):
        return "mots_cles_absents"
    if o.teletravail and not config.inclure_teletravail:
        return "teletravail"
    return None


def prefiltrer(offres: list[Offre], config: Config, now: datetime) -> list[Offre]:
    """Pose `motif_rejet` ; garde toutes les offres. Un motif déjà posé (ex. hors_zone) est conservé."""
    return [
        o if o.motif_rejet else o.model_copy(update={"motif_rejet": _motif(o, config, now)}) for o in offres
    ]
