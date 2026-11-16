import os
from collections.abc import Mapping
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field


class Centre(BaseModel):
    commune: str
    insee: str
    lat: float
    lon: float


class PisteAlternance(BaseModel):
    romes: list[str]
    duree_mois: list[int]
    frequence_heures: int = Field(gt=0)


class PisteStage(BaseModel):
    duree_mois: list[int]
    debut: list[str]
    frequence_heures: int = Field(gt=0)


class Pistes(BaseModel):
    alternance: PisteAlternance
    stage: PisteStage


class LLMCall(BaseModel):
    effort: Literal["low", "medium", "high"]
    max_tokens: int = Field(gt=0)


class Prix(BaseModel):
    input: float
    output: float
    cache_write: float
    cache_read: float


class LLMConfig(BaseModel):
    modele: str
    scoring: LLMCall
    ecriture: LLMCall
    llm_max_appels_jour: int = Field(gt=0)
    llm_budget_mensuel_eur: float = Field(gt=0)
    prix_usd_par_mtok: Prix
    taux_usd_eur: float = Field(gt=0)


class Config(BaseModel):
    centre: Centre
    rayon_km: float = Field(gt=0)
    inclure_teletravail_complet: bool
    niveau_vise: str
    pistes: Pistes
    mots_cles_titre: list[str]
    mots_exclus: list[str]
    mots_bonus: list[str]
    age_max_jours: int = Field(gt=0)
    score_min: int = Field(ge=0, le=100)
    alerte_immediate_alternance_min: int = Field(ge=0, le=100)
    digest_max_offres: int = Field(gt=0)
    plage_alertes: list[str]
    heure_digest: str
    llm: LLMConfig


class Secrets(BaseModel):
    lba_api_key: str | None = None
    anthropic_api_key: str | None = None
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    telegram_webhook_secret: str | None = None
    adzuna_app_id: str | None = None
    adzuna_app_key: str | None = None
    database_url: str = "sqlite:///denicheur.db"
    gmail_user: str | None = None
    gmail_app_password: str | None = None
    dashboard_password: str | None = None
    ft_client_id: str | None = None
    ft_client_secret: str | None = None

    @property
    def adzuna_enabled(self) -> bool:
        return bool(self.adzuna_app_id and self.adzuna_app_key)


def load_config(path: Path | str) -> Config:
    with open(path, encoding="utf-8") as f:
        return Config.model_validate(yaml.safe_load(f))


def load_secrets(env: Mapping[str, str] = os.environ) -> Secrets:
    # Une variable vide équivaut à absente (.env.example a des valeurs vides).
    valeurs = {k: env[k.upper()] for k in Secrets.model_fields if env.get(k.upper())}
    return Secrets(**valeurs)
