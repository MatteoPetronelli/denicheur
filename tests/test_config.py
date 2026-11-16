import json
import re
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from denicheur.config import load_config, load_secrets

RACINE = Path(__file__).parent.parent
YAML = RACINE / "config" / "recherches.yaml"


def test_load_config_valide():
    cfg = load_config(YAML)
    assert cfg.rayon_km == 25
    assert cfg.niveau_vise == "6"


def test_llm_ollama():
    llm = load_config(YAML).llm
    assert llm.fournisseur == "ollama"
    assert llm.url == "http://localhost:11434"
    assert llm.scoring.modele == "llama3.1:8b"
    assert llm.scoring.temperature == 0.0
    assert llm.ecriture.temperature == 0.7
    assert llm.llm_max_appels_jour == 150
    assert llm.llm_max_duree_run_s == 900


@pytest.mark.parametrize("champ", ["llm_budget_mensuel_eur", "prix_usd_par_mtok"])
def test_champs_facturation_rejetes(tmp_path, champ):
    data = yaml.safe_load(YAML.read_text(encoding="utf-8"))
    data["llm"][champ] = 1
    f = tmp_path / "r.yaml"
    f.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ValidationError):
        load_config(f)


def test_rayon_negatif_rejete(tmp_path):
    data = yaml.safe_load(YAML.read_text(encoding="utf-8"))
    data["rayon_km"] = -1
    f = tmp_path / "r.yaml"
    f.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ValidationError):
        load_config(f)


def test_adzuna_desactive_sans_cles():
    assert load_secrets({}).adzuna_enabled is False
    assert load_secrets({"ADZUNA_APP_ID": "a", "ADZUNA_APP_KEY": "b"}).adzuna_enabled is True


def test_cles_cloud_ignorees():
    assert not hasattr(load_secrets({"ANTHROPIC_API_KEY": "x"}), "anthropic_api_key")


def test_database_url_vide_donne_defaut():
    assert load_secrets({"DATABASE_URL": ""}).database_url == "sqlite:///denicheur.db"


def test_database_url_par_defaut():
    assert load_secrets({}).database_url == "sqlite:///denicheur.db"
    assert load_secrets({"DATABASE_URL": "postgres://x"}).database_url == "postgres://x"


def test_profil_sans_pii():
    texte = (RACINE / "profile" / "profil.md").read_text(encoding="utf-8")
    assert not re.search(r"0\d[\s.]?\d{2}[\s.]?\d{2}", texte)
    assert "@" not in texte
    assert "né le" not in texte.lower()


def test_fixture_lba():
    data = json.loads((RACINE / "tests" / "fixtures" / "lba_search.json").read_text(encoding="utf-8"))
    assert len(data["jobs"]) == 16
    assert len(data["recruiters"]) == 150


def test_stage_lieu_et_mots_cles():
    stage = load_config(YAML).pistes.stage
    assert stage.lieu_recherche == "Marly-le-Roi"  # Adzuna ne connaît pas Mareil-Marly
    assert 1 <= len(stage.mots_cles_recherche) <= 10


@pytest.mark.parametrize("mots", [[], [f"mot{i}" for i in range(11)]])
def test_mots_cles_stage_bornes(tmp_path, mots):
    data = yaml.safe_load(YAML.read_text(encoding="utf-8"))
    data["pistes"]["stage"]["mots_cles_recherche"] = mots
    f = tmp_path / "r.yaml"
    f.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ValidationError):
        load_config(f)


def test_dix_mots_cles_acceptes(tmp_path):
    data = yaml.safe_load(YAML.read_text(encoding="utf-8"))
    data["pistes"]["stage"]["mots_cles_recherche"] = [f"mot{i}" for i in range(10)]
    f = tmp_path / "r.yaml"
    f.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    assert len(load_config(f).pistes.stage.mots_cles_recherche) == 10
