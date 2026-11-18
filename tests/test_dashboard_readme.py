from pathlib import Path

README = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")


def test_le_readme_interdit_d_exposer_le_port_du_tableau_de_bord():
    assert "## Tableau de bord" in README
    assert "Ne jamais exposer le port" in README
    assert "127.0.0.1" in README
