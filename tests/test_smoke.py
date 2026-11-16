import logging
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
    for cle in (
        "LBA_API_KEY",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
        "GMAIL_USER",
        "GMAIL_APP_PASSWORD",
        "ADZUNA_APP_ID",
        "ADZUNA_APP_KEY",
    ):
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


def test_run_sans_mot_de_passe_aucune_connexion_imap(tmp_path, monkeypatch, capsys):
    _env_sans_reseau(tmp_path, monkeypatch)
    monkeypatch.setenv("GMAIL_USER", "moi@exemple.fr")  # mot de passe absent

    def interdit(*a, **k):
        raise AssertionError("connexion IMAP sans mot de passe")

    monkeypatch.setattr("imaplib.IMAP4_SSL", interdit)
    assert main(["run", "--mode", "alternance", "--dry-run"]) == 0
    assert "Erreur" not in capsys.readouterr().out


def test_run_avec_identifiants_la_source_email_est_collectee(tmp_path, monkeypatch, capsys):
    _env_sans_reseau(tmp_path, monkeypatch)
    monkeypatch.setenv("GMAIL_USER", "moi@exemple.fr")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "secret")
    appels = []

    def faux_lire(user, password, since):
        appels.append((user, password))
        return []

    monkeypatch.setattr("denicheur.__main__.lire_alertes", faux_lire)
    assert main(["run", "--mode", "alternance", "--dry-run"]) == 0
    assert appels == [("moi@exemple.fr", "secret")]


@pytest.mark.parametrize("present", ["ADZUNA_APP_ID", "ADZUNA_APP_KEY"])
def test_run_avec_une_seule_valeur_adzuna_aucune_requete(tmp_path, monkeypatch, capsys, present):
    _env_sans_reseau(tmp_path, monkeypatch)
    monkeypatch.setenv(present, "valeur-seule")
    appels = []
    monkeypatch.setattr("denicheur.__main__.adzuna.collecter", lambda *a, **k: appels.append(a) or [])
    assert main(["run", "--mode", "stage", "--dry-run"]) == 0
    assert appels == [] and "Erreur" not in capsys.readouterr().out


def test_run_avec_cles_adzuna_la_source_est_appelee_sans_cle_lba(tmp_path, monkeypatch, capsys):
    _env_sans_reseau(tmp_path, monkeypatch)
    monkeypatch.setenv("LBA_API_KEY", "cle-lba-secrete")
    monkeypatch.setenv("ADZUNA_APP_ID", "mon-id")
    monkeypatch.setenv("ADZUNA_APP_KEY", "ma-cle")
    appels = []

    def faux(config, http, now, app_id, app_key):
        appels.append((app_id, app_key, dict(http.headers)))
        return []

    monkeypatch.setattr("denicheur.__main__.adzuna.collecter", faux)
    assert main(["run", "--mode", "stage", "--dry-run"]) == 0
    assert [(a, k) for a, k, _ in appels] == [("mon-id", "ma-cle")]
    assert "authorization" not in {h.lower() for h in appels[0][2]}  # la clé LBA ne part pas chez Adzuna
    sortie = capsys.readouterr().out
    assert "ma-cle" not in sortie and "mon-id" not in sortie


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


def test_bot_sans_chat_id_aide_et_code_1_sans_reseau(tmp_path, monkeypatch, capsys):
    _env_sans_reseau(tmp_path, monkeypatch)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")

    def interdit(*a, **k):
        raise AssertionError("aucun appel réseau attendu")

    monkeypatch.setattr(TelegramAPI, "get_updates", interdit)
    monkeypatch.setattr(TelegramAPI, "delete_webhook", interdit)
    assert main(["bot"]) == 1
    assert "TELEGRAM_CHAT_ID" in capsys.readouterr().out


def test_bot_sans_jeton_code_1(tmp_path, monkeypatch, capsys):
    _env_sans_reseau(tmp_path, monkeypatch)
    assert main(["bot"]) == 1
    assert "TELEGRAM_BOT_TOKEN" in capsys.readouterr().out


def test_bot_lance_la_boucle_pour_le_chat_configure(tmp_path, monkeypatch):
    _env_sans_reseau(tmp_path, monkeypatch)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "77")
    recu = []
    monkeypatch.setattr("denicheur.__main__.boucle", recu.append)
    assert main(["bot"]) == 0
    assert recu[0].chat_id == "77"
    for nom in ("httpx", "httpcore"):  # leurs URL contiennent le jeton du bot
        assert logging.getLogger(nom).getEffectiveLevel() >= logging.WARNING
