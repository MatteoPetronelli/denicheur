"""Recherche d'entreprises (API publique, sans clé) : PME informatiques autour du centre."""

import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import httpx
from sqlalchemy.orm import Session

from denicheur.config import Config
from denicheur.db import repo
from denicheur.http import get_json
from denicheur.models import SIRET_RE, Entreprise
from denicheur.pipeline.geo import haversine_km

URL = "https://recherche-entreprises.api.gouv.fr/search"
PAUSE_S = 0.2  # la limite de l'API est de 7 appels par seconde
_SIRET = re.compile(SIRET_RE)
# Code INSEE de tranche d'effectif -> (bas, haut, libellé) ; le CSV de l'utilisateur écrit « 0-0 » pour zéro.
TRANCHES: dict[str, tuple[int, int, str]] = {
    "00": (0, 0, "0-0"), "01": (1, 2, "1-2"), "02": (3, 5, "3-5"), "03": (6, 9, "6-9"),
    "11": (10, 19, "10-19"), "12": (20, 49, "20-49"), "21": (50, 99, "50-99"),
    "22": (100, 199, "100-199"), "31": (200, 249, "200-249"), "32": (250, 499, "250-499"),
    "41": (500, 999, "500-999"), "42": (1000, 1999, "1000-1999"), "51": (2000, 4999, "2000-4999"),
    "52": (5000, 9999, "5000-9999"), "53": (10000, 10**9, "10000+"),
}  # fmt: skip
NAF_LIBELLES = {
    "62.01Z": "Programmation informatique",
    "62.02A": "Conseil en systèmes et logiciels informatiques",
    "58.29C": "Édition de logiciels applicatifs",
    "63.11Z": "Traitement de données, hébergement et activités connexes",
}


class ErreurRecherche(Exception):
    """Panne ou réponse inutilisable de l'API ; le message ne contient ni URL ni donnée reçue."""


@dataclass
class BilanRecherche:
    creees: int = 0
    mises_a_jour: int = 0
    ignorees: int = 0
    erreurs: list[str] = field(default_factory=list)


def tranches_entre(mini: int, maxi: int) -> list[str]:
    """Codes de tranche d'effectif entièrement compris entre `mini` et `maxi` salariés."""
    return [code for code, (bas, haut, _) in TRANCHES.items() if bas >= mini and haut <= maxi]


def _coordonnees(e: dict[str, Any]) -> tuple[float, float] | None:
    try:
        return float(e["latitude"]), float(e["longitude"])
    except (KeyError, TypeError, ValueError):
        return None


def convertir(unite: dict[str, Any], config: Config) -> Entreprise | None:
    """L'établissement en activité le plus proche du centre, s'il est dans le rayon ; sinon None.

    Seuls nom, activité, effectif et l'établissement choisi sont lus : jamais les dirigeants.
    """
    candidats = [*(unite.get("matching_etablissements") or []), unite.get("siege") or {}]
    meilleur: tuple[float, dict[str, Any], tuple[float, float]] | None = None
    for e in candidats:
        position = _coordonnees(e)
        siret = e.get("siret")
        if e.get("etat_administratif") != "A" or position is None:
            continue
        if not isinstance(siret, str) or not _SIRET.fullmatch(siret):
            continue
        distance = haversine_km(config.centre.lat, config.centre.lon, *position)
        if distance <= config.rayon_km and (meilleur is None or distance < meilleur[0]):
            meilleur = (distance, e, position)
    nom, naf = unite.get("nom_complet"), unite.get("activite_principale")
    if meilleur is None or not isinstance(nom, str) or not nom or not isinstance(naf, str):
        return None
    distance, e, (lat, lon) = meilleur
    tranche = TRANCHES.get(str(unite.get("tranche_effectif_salarie")))
    return Entreprise(
        siret=e["siret"],
        nom=nom,
        activite=NAF_LIBELLES.get(naf, naf),
        naf=naf,
        effectif=tranche[2] if tranche else None,
        adresse=e.get("adresse") or None,
        commune=e.get("libelle_commune") or None,
        lat=lat,
        lon=lon,
        distance_km=round(distance, 1),
        origine="sirene",
    )


def lire_page(
    config: Config, http: httpx.Client, departement: str, naf: str, page: int,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[list[Entreprise], int, int]:  # fmt: skip
    """(entreprises retenues, nombre total de pages, nombre d'unités écartées) d'une page de résultats."""
    e = config.entreprises
    params = {
        "departement": departement,
        "activite_principale": naf,
        "etat_administratif": "A",
        "tranche_effectif_salarie": ",".join(tranches_entre(e.effectif_min, e.effectif_max)),
        "per_page": 25,
        "page": page,
    }
    try:
        data = get_json(http, URL, params=params, sleep=sleep)
        unites = data["results"]
        total_pages = int(data["total_pages"])
        retenues = [x for u in unites if (x := convertir(u, config)) is not None]
    except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError) as err:
        raise ErreurRecherche(type(err).__name__) from None
    sleep(PAUSE_S)
    return retenues, total_pages, len(unites) - len(retenues)


def actualiser_couple(
    session: Session, config: Config, http: httpx.Client, departement: str, naf: str, now: datetime,
    sleep: Callable[[float], None] = time.sleep,
) -> BilanRecherche:  # fmt: skip
    """Lit au plus `pages_max` pages à partir du curseur du couple et l'avance ; échec : curseur inchangé."""
    cle = f"curseur_entreprises:{departement}:{naf}"
    page = int(repo.get_param(session, cle) or 1)
    bilan = BilanRecherche()
    suivant = page
    for _ in range(config.entreprises.pages_max):
        retenues, total_pages, ignorees = lire_page(config, http, departement, naf, page, sleep)
        bilan.ignorees += ignorees
        for entreprise in retenues:
            _, creee = repo.enregistrer_entreprise(session, entreprise, now)
            bilan.creees += creee
            bilan.mises_a_jour += not creee
        if page >= total_pages:
            suivant = 1
            break
        page += 1
        suivant = page
    repo.set_param(session, cle, str(suivant))
    return bilan


def actualiser(
    session: Session, config: Config, http: httpx.Client, now: datetime,
    sleep: Callable[[float], None] = time.sleep,
) -> BilanRecherche:  # fmt: skip
    """Tous les couples département-NAF ; à la première panne, on s'arrête (l'API est sans doute en panne)."""
    total = BilanRecherche()
    for departement in config.entreprises.departements:
        for naf in config.entreprises.naf:
            try:
                bilan = actualiser_couple(session, config, http, departement, naf, now, sleep)
            except ErreurRecherche as err:
                session.rollback()
                total.erreurs.append(f"recherche entreprises {departement} {naf} : {type(err).__name__}")
                return total
            session.commit()
            total.creees += bilan.creees
            total.mises_a_jour += bilan.mises_a_jour
            total.ignorees += bilan.ignorees
    return total
