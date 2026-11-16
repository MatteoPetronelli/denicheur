import hashlib
import logging
import re
import unicodedata
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from email.message import Message

import httpx

from denicheur.config import Config
from denicheur.mail.parsers import OffreMail, analyser
from denicheur.models import Offre, Piste

GEOCODAGE = "https://api-adresse.data.gouv.fr/search/"
# shortcut : fenêtre glissante sans état, le dédoublonnage absorbe les recouvrements.
FENETRE = timedelta(days=7)
log = logging.getLogger(__name__)

_ALTERNANCE = ("alternance", "apprentissage", "apprenti", "alternant")
_STAGE = ("stage", "stagiaire")
_TELETRAVAIL = re.compile(r"t[ée]l[ée]travail|hybride|remote", re.IGNORECASE)


def _sans_accent(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def piste_du_titre(titre: str) -> Piste:
    t = _sans_accent(titre)
    if any(m in t for m in _ALTERNANCE):
        return Piste.ALTERNANCE
    if any(m in t for m in _STAGE):
        return Piste.STAGE
    return Piste.AUTRE


def _geocoder(http: httpx.Client, ville: str, dep: str) -> tuple[float, float] | None:
    for _ in range(2):  # un échec ponctuel de l'API ne doit pas faire perdre la distance
        try:
            r = http.get(GEOCODAGE, params={"q": f"{ville} {dep}", "type": "municipality", "limit": 1})
            r.raise_for_status()
            lon, lat = r.json()["features"][0]["geometry"]["coordinates"]
            return lat, lon
        except (httpx.HTTPError, KeyError, IndexError, ValueError):
            continue
    return None  # lieu à vérifier : jamais d'échec de collecte pour un géocodage


def _offre(o: OffreMail, coord: tuple[float, float] | None) -> Offre:
    lat, lon = coord or (None, None)
    return Offre(
        source=f"email:{o.site}",
        source_id=hashlib.sha1(o.lien.encode()).hexdigest(),
        url=o.lien,
        titre=o.titre,
        entreprise=o.entreprise,
        commune=o.ville,
        lat=lat,
        lon=lon,
        piste=piste_du_titre(o.titre),
        duree_mois=None,
        debut=None,
        niveau_diplome=None,
        description=o.texte,
        teletravail=bool(_TELETRAVAIL.search(f"{o.titre} {o.texte}")),
        publiee_le=None,
        expire_le=None,
    )


def collecter(
    config: Config,
    now: datetime,
    lire: Callable[[datetime], list[Message]] | None,
    http: httpx.Client,
) -> list[Offre]:
    if lire is None:
        log.info("Identifiants Gmail absents : source e-mail ignorée")
        return []
    since = now.astimezone(UTC).replace(tzinfo=None) - FENETRE
    cache: dict[tuple[str, str], tuple[float, float] | None] = {}
    offres = []
    for msg in lire(since):
        for o in analyser(msg):
            cle = (o.ville, o.departement)
            if cle not in cache:
                cache[cle] = _geocoder(http, *cle)
            offres.append(_offre(o, cache[cle]))
    return offres
