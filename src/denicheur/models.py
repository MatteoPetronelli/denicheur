from datetime import date, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class Piste(StrEnum):
    STAGE = "stage"
    ALTERNANCE = "alternance"
    AUTRE = "autre"


class Statut(StrEnum):
    """Suivi d'une candidature ; « nouvelle » = pas de ligne `candidatures`."""

    INTERESSANTE = "interessante"
    CANDIDATURE_ENVOYEE = "candidature_envoyee"
    RELANCEE = "relancee"
    ENTRETIEN = "entretien"
    REFUS = "refus"
    OFFRE = "offre"
    SANS_REPONSE = "sans_reponse"
    IGNOREE = "ignoree"


class Offre(BaseModel):
    source: str
    source_id: str
    url: str
    titre: str
    entreprise: str | None
    siret: str | None = None  # SIRET de l'employeur, quand la source le donne
    commune: str | None
    lat: float | None
    lon: float | None
    piste: Piste
    duree_mois: int | None
    debut: date | None
    debut_des_que_possible: bool = False
    niveau_diplome: str | None
    description: str
    # Télétravail, même partiel. Non persisté : sert au préfiltre uniquement.
    teletravail: bool = False
    publiee_le: datetime | None
    expire_le: datetime | None
    # Renseignés par le pipeline.
    distance_km: float | None = None
    lieu_a_verifier: bool = False
    motif_rejet: str | None = None


class ScoreLLM(BaseModel):
    """Sortie structurée du LLM (spec §6)."""

    score: int = Field(ge=0, le=100)
    type: Literal["stage", "alternance", "autre"]
    points_forts: list[str]
    points_faibles: list[str]
    alerte: str | None
    projet_a_citer: str
    resume: str


SIRET_RE = r"^[0-9]{14}$"


class Entreprise(BaseModel):
    """Entreprise à démarcher sans offre ; les champs d'état (listée, contactée, écartée) restent en base."""

    siret: str = Field(pattern=SIRET_RE)
    nom: str = Field(min_length=1)
    activite: str | None = None
    naf: str | None = None
    effectif: str | None = None
    adresse: str | None = None
    commune: str | None = None
    lat: float | None = None
    lon: float | None = None
    distance_km: float | None = None
    priorite: int | None = None
    url_candidature: str | None = None
    origine: Literal["csv", "lba", "sirene"]
