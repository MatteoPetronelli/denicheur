import re
from functools import cache
from math import asin, cos, radians, sin, sqrt
from pathlib import Path

from denicheur.config import Config
from denicheur.models import Offre
from denicheur.pipeline.normalize import normaliser_texte as norm

VILLES = Path(__file__).resolve().parents[3] / "config" / "villes_hors_zone.txt"


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = radians(lat1), radians(lat2)
    a = sin((p2 - p1) / 2) ** 2 + cos(p1) * cos(p2) * sin(radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371.0088 * asin(sqrt(a))


@cache
def _villes_regex() -> re.Pattern[str]:
    villes = [norm(v) for v in VILLES.read_text(encoding="utf-8").splitlines() if v.strip()]
    return re.compile(r"(?<!\w)(" + "|".join(re.escape(v) for v in villes) + r")(?!\w)")


def appliquer_geo(offres: list[Offre], config: Config) -> list[Offre]:
    # shortcut: liste fixe de villes ; géocoder les mentions si des faux positifs apparaissent.
    sortie = []
    for o in offres:
        maj: dict = {}
        if o.lat is None or o.lon is None:
            maj["lieu_a_verifier"] = True
        else:
            d = haversine_km(config.centre.lat, config.centre.lon, o.lat, o.lon)
            maj["distance_km"] = d
            if d > config.rayon_km:
                maj["motif_rejet"] = "hors_zone"
        villes = set(_villes_regex().findall(norm(o.description)))
        if villes - {norm(o.commune)}:
            maj["lieu_a_verifier"] = True
        sortie.append(o.model_copy(update=maj))
    return sortie
