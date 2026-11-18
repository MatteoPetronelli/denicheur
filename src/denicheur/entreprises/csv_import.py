"""Import du CSV d'entreprises de l'utilisateur ; rejouable sans risque (upsert par SIRET)."""

import csv
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy.orm import Session

from denicheur.db import repo
from denicheur.models import Entreprise

_COMMUNE = re.compile(r"\b\d{5}\s+(.+)$")


@dataclass
class BilanImport:
    creees: int = 0
    mises_a_jour: int = 0
    ignorees: int = 0


def _nombre(texte: str, type_: type[int] | type[float]) -> int | float | None:
    try:
        return type_(texte.strip().replace(",", "."))
    except ValueError:
        return None


def _entreprise(ligne: dict[str, str]) -> Entreprise:
    adresse = (ligne.get("adresse") or "").strip()
    commune = _COMMUNE.search(adresse)

    def champ(nom: str) -> str | None:
        return (ligne.get(nom) or "").strip() or None

    return Entreprise(
        siret=(ligne.get("siret") or "").strip(),
        nom=(ligne.get("entreprise") or "").strip(),
        activite=champ("activite"),
        naf=champ("naf"),
        effectif=champ("effectif"),
        adresse=adresse or None,
        commune=commune.group(1) if commune else None,
        distance_km=_nombre(ligne.get("distance_km") or "", float),  # type: ignore[arg-type]
        priorite=_nombre(ligne.get("rang") or "", int),  # type: ignore[arg-type]
        url_candidature=champ("candidature_spontanee_url"),
        origine="csv",
    )


def importer_csv(session: Session, chemin: Path, now: datetime) -> BilanImport:
    """Lit le CSV (`utf-8-sig`, séparateur « ; ») ; une ligne sans SIRET valide ou sans nom est ignorée."""
    bilan = BilanImport()
    with chemin.open(encoding="utf-8-sig", newline="") as f:
        for ligne in csv.DictReader(f, delimiter=";"):
            try:
                entreprise = _entreprise(ligne)
            except ValidationError:
                bilan.ignorees += 1
                continue
            _, creee = repo.enregistrer_entreprise(session, entreprise, now)
            if creee:
                bilan.creees += 1
            else:
                bilan.mises_a_jour += 1
    return bilan
