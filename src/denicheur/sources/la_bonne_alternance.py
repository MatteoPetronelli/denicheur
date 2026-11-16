import logging
import re
from datetime import date, datetime
from typing import Any

import httpx

from denicheur.config import Config
from denicheur.http import get_json
from denicheur.models import Offre, Piste

URL = "https://api.apprentissage.beta.gouv.fr/api/job/v1/search"
log = logging.getLogger(__name__)
_COMMUNE = re.compile(r"\b\d{5}\s+(.+)$")


def _rechercher(config: Config, http: httpx.Client) -> dict[str, Any] | None:
    # La clé est portée par le client (en-tête Authorization) ; absente = source désactivée.
    if "Authorization" not in http.headers:
        log.info("LBA_API_KEY absente : source la_bonne_alternance ignorée")
        return None
    params = {
        "latitude": config.centre.lat,
        "longitude": config.centre.lon,
        "radius": config.rayon_km,
        "romes": ",".join(config.pistes.alternance.romes),
    }
    return get_json(http, URL, params=params)


def _dt(s: str | None) -> datetime | None:
    return datetime.fromisoformat(s) if s else None


def _offre(j: dict[str, Any]) -> Offre:
    w, c, o = j["workplace"], j["contract"], j["offer"]
    lon, lat = w["location"]["geopoint"]["coordinates"]  # [lon, lat]
    m = _COMMUNE.search(w["location"].get("address") or "")
    precise = c.get("start_type") == "precise_date" and c.get("start")
    pub = o.get("publication") or {}
    return Offre(
        source="lba",
        source_id=j["identifier"]["id"],
        url=j["apply"]["url"],
        titre=o["title"],
        entreprise=w.get("name") or w.get("legal_name") or w.get("brand"),
        commune=m.group(1) if m else None,
        lat=lat,
        lon=lon,
        piste=Piste.ALTERNANCE,
        duree_mois=c.get("duration"),
        debut=date.fromisoformat(c["start"][:10]) if precise else None,
        debut_des_que_possible=c.get("start_type") == "des_que_possible",
        niveau_diplome=(o.get("target_diploma") or {}).get("european"),
        description=o.get("description") or "",
        # Présentiel exigé par l'école : tout `remote` autre que absent/onsite écarte l'offre.
        teletravail=c.get("remote") not in (None, "onsite"),
        publiee_le=_dt(pub.get("creation")),
        expire_le=_dt(pub.get("expiration")),
    )


def collecter(config: Config, http: httpx.Client, now: datetime) -> list[Offre]:
    data = _rechercher(config, http)
    return [_offre(j) for j in data["jobs"]] if data else []


def collecter_recruteurs(config: Config, http: httpx.Client) -> list[dict[str, Any]]:
    data = _rechercher(config, http)
    return data["recruiters"] if data else []
