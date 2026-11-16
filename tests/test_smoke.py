from sqlalchemy import inspect

import denicheur
from denicheur.__main__ import main
from denicheur.db.base import make_engine


def test_package_imports():
    assert denicheur.__doc__


def test_stub_command(capsys):
    assert main(["stats"]) == 0
    assert "non implémenté" in capsys.readouterr().out


def test_init_db_migre_la_base(tmp_path, monkeypatch, capsys):
    url = f"sqlite:///{tmp_path / 'cli.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    assert main(["init-db"]) == 0
    assert "non implémenté" not in capsys.readouterr().out
    assert "offres" in inspect(make_engine(url)).get_table_names()
