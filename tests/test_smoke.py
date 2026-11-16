from pathlib import Path

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

import denicheur
from denicheur.__main__ import main
from denicheur.db.base import make_engine
from denicheur.telegram.api import TelegramAPI


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


def _env_sans_reseau(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'run.db'}")
    for cle in ("LBA_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"):
        monkeypatch.setenv(cle, "")  # vide = absent ; load_dotenv n'écrase pas


def test_run_mode_invalide_refuse():
    with pytest.raises(SystemExit) as e:
        main(["run", "--mode", "inconnu"])
    assert e.value.code == 2


def test_run_dry_run_sans_envoi(tmp_path, monkeypatch, capsys):
    _env_sans_reseau(tmp_path, monkeypatch)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")

    def interdit(*a, **k):
        raise AssertionError("envoi Telegram en dry-run")

    monkeypatch.setattr(TelegramAPI, "send_message", interdit)
    assert main(["run", "--dry-run"]) == 0
    assert "dry-run" in capsys.readouterr().out
    with Session(make_engine(f"sqlite:///{tmp_path / 'run.db'}")) as s:
        assert s.execute(text("select count(*) from executions")).scalar() == 1


def test_run_echec_code_1(tmp_path, monkeypatch, capsys):
    _env_sans_reseau(tmp_path, monkeypatch)

    def casse(*a, **k):
        raise RuntimeError("x")

    monkeypatch.setattr("denicheur.scoring.service.scorer_offres", casse)
    monkeypatch.setattr("denicheur.pipeline.run.scorer_offres", casse)
    assert main(["run", "--dry-run"]) == 1
    assert "échec" in capsys.readouterr().out


def test_aucun_smtplib_dans_src():
    # L'envoi de candidature reste humain : le code ne parle jamais SMTP.
    racine = Path(__file__).parent.parent / "src"
    assert not [p for p in racine.rglob("*.py") if "smtplib" in p.read_text(encoding="utf-8")]
