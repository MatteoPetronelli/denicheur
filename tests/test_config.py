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
    assert cfg.llm.modele == "claude-sonnet-5-5"
    assert cfg.llm.scoring.effort == "low"
    assert cfg.llm.ecriture.effort == "medium"


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
