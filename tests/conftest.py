"""Fixtures partagées entre fichiers de tests."""

import pytest


@pytest.fixture
def profil(tmp_path):
    (tmp_path / "regles_ecriture.md").write_text("REGLES-SENTINELLE", encoding="utf-8")
    (tmp_path / "lettre_modele.md").write_text("MODELE-SENTINELLE", encoding="utf-8")
    (tmp_path / "profil.md").write_text("PROFIL-SENTINELLE", encoding="utf-8")
    (tmp_path / "cv_stage.md").write_text("CV-SECRET 06 13 72 02 11 moi@exemple.fr", encoding="utf-8")
    return tmp_path
