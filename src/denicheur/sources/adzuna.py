import re
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import httpx

from denicheur.config import Config
from denicheur.http import get_json
from denicheur.mail.parsers import lien_propre
from denicheur.models import Offre, Piste
from denicheur.sources.texte import est_teletravail, piste_dans

URL = "https://api.adzuna.com/v1/api/jobs/fr/search/1"
_DUREE = re.compile(r"(\d{1,2})\s*mois", re.IGNORECASE)


class ErreurAdzuna(Exception):
    """Erreur sans URL : Adzuna reçoit app_id et app_key dans la requête, donc dans l'URL."""


def _recherche(
    http: httpx.Client, config: Config, mot: str, app_id: str, app_key: str, sleep: Callable[[float], None]
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {
        "app_id": app_id,
        "app_key": app_key,
        "what": f"{mot} stage",
        "where": config.pistes.stage.lieu_recherche,
        "distance": config.rayon_km,
        "max_days_old": config.age_max_jours,
        "results_per_page": 50,
    }
    try:
        return get_json(http, URL, params=params, sleep=sleep)["results"]
    except httpx.HTTPStatusError as e:
        raise ErreurAdzuna(f"HTTP {e.response.status_code}") from None


def _commune(display_name: str) -> str | None:
    parties = [p.strip() for p in display_name.split(",") if p.strip()]
    if len(parties) > 1 and re.search("arrondissement", parties[0], re.IGNORECASE):
        return parties[1]  # « 9ème Arrondissement, Paris » : la commune est la suivante
    return parties[0] if parties else None


def _duree(titre: str, description: str) -> int | None:
    for texte in (titre, description):
        m = _DUREE.search(texte)
        if m:
            return int(m[1])
    return None


def _offre(r: dict[str, Any]) -> Offre:
    titre, description = r["title"], r.get("description") or ""
    piste = piste_dans(titre, stage_d_abord=True) or piste_dans(description, stage_d_abord=True)
    cree = datetime.fromisoformat(r["created"]).astimezone(UTC) if r.get("created") else None
    return Offre(
        source="adzuna",
        source_id=str(r["id"]),
        url=lien_propre(r["redirect_url"]),  # retire utm_source, qui porte l'App ID
        titre=titre,
        entreprise=(r.get("company") or {}).get("display_name"),
        commune=_commune((r.get("location") or {}).get("display_name") or ""),
        lat=r.get("latitude"),
        lon=r.get("longitude"),
        piste=piste or Piste.AUTRE,
        duree_mois=_duree(titre, description),
        debut=None,
        niveau_diplome=None,
        description=description,
        teletravail=est_teletravail(f"{titre} {description}"),
        publiee_le=cree,
        expire_le=None,
    )


def collecter(
    config: Config,
    http: httpx.Client,
    now: datetime,
    app_id: str,
    app_key: str,
    *,
    sleep: Callable[[float], None] = time.sleep,
) -> list[Offre]:
    vues: dict[str, Offre] = {}
    for mot in config.pistes.stage.mots_cles_recherche:
        for r in _recherche(http, config, mot, app_id, app_key, sleep):
            vues.setdefault(str(r["id"]), _offre(r))
    return list(vues.values())
