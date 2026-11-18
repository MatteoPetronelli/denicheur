"""Recruteurs de La bonne alternance (candidatures spontanées) convertis en entreprises."""

import re
from typing import Any

from pydantic import ValidationError

from denicheur.config import Config
from denicheur.models import Entreprise
from denicheur.pipeline.geo import haversine_km

_COMMUNE = re.compile(r"\b\d{5}\s+(.+)$")


def _borne_haute(taille: object) -> int | None:
    """Borne haute d'une tranche « 20-49 » ; None si la tranche est absente ou illisible."""
    if not isinstance(taille, str):
        return None
    morceaux = taille.split("-")
    return int(morceaux[-1]) if morceaux[-1].isdigit() else None


def _convertir(r: dict[str, Any], config: Config) -> Entreprise | None:
    w = r.get("workplace") or {}
    naf = (w.get("domain") or {}).get("naf") or {}
    if naf.get("code") not in config.entreprises.naf:
        return None
    borne = _borne_haute(w.get("size"))
    if borne is not None and borne > config.entreprises.effectif_max:
        return None
    point = (w.get("location") or {}).get("geopoint") or {}
    try:
        lon, lat = point["coordinates"]
        adresse = (w.get("location") or {}).get("address") or ""
        commune = _COMMUNE.search(adresse)
        return Entreprise(
            siret=w.get("siret") or "",
            nom=w.get("name") or w.get("legal_name") or w.get("brand") or "",
            activite=naf.get("label"),
            naf=naf["code"],
            effectif=w.get("size"),
            adresse=adresse or None,
            commune=commune.group(1) if commune else None,
            lat=lat,
            lon=lon,
            distance_km=round(haversine_km(config.centre.lat, config.centre.lon, lat, lon), 1),
            url_candidature=(r.get("apply") or {}).get("url"),
            origine="lba",
        )
    except (KeyError, TypeError, ValueError, ValidationError):
        return None


def depuis_recruteurs(recruteurs: list[dict[str, Any]], config: Config) -> tuple[list[Entreprise], int]:
    """(entreprises retenues, nombre d'écartées) : hors activités, trop grandes ou incomplètes."""
    retenues = [e for r in recruteurs if (e := _convertir(r, config)) is not None]
    return retenues, len(recruteurs) - len(retenues)
