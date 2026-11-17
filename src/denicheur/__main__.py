import argparse
import logging
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from denicheur.config import Secrets, load_config, load_secrets
from denicheur.db.base import make_engine, migrer
from denicheur.mail.imap import lire_alertes
from denicheur.pipeline.run import MODES, Deps, Source, executer
from denicheur.redaction.documents import DOSSIER_LETTRES
from denicheur.redaction.gmail_drafts import Piece, creer_brouillon
from denicheur.redaction.service import Redacteur
from denicheur.scoring.llm import OllamaScorer
from denicheur.sources import SOURCES, adzuna, email_alertes
from denicheur.telegram.api import TelegramAPI, TelegramError
from denicheur.telegram.bot import BotDeps, boucle
from denicheur.telegram.digest import envoyer_digest, envoyer_test

COMMANDES = ("stats",)
CONFIG = Path(__file__).resolve().parents[2] / "config" / "recherches.yaml"


def _setup_telegram(api: TelegramAPI) -> int:
    chats = {u["message"]["chat"]["id"]: u["message"]["chat"] for u in api.get_updates() if "message" in u}
    if not chats:
        print("Aucun message reçu : écris /start à ton bot dans Telegram, puis relance.")
        return 1
    for chat_id, chat in chats.items():
        print(f"chat.id : {chat_id} ({chat.get('first_name') or chat.get('title') or '?'})")
    print("Copie la valeur dans TELEGRAM_CHAT_ID (.env).")
    return 0


def _lier(collecter, http: httpx.Client) -> Source:
    return lambda config, now: collecter(config, http, now)


def _source_email(user: str, password: str) -> Source:
    # Client distinct : la clé LBA ne doit pas partir vers api-adresse.
    geo = httpx.Client()
    return lambda config, now: email_alertes.collecter(
        config, now, lambda since: lire_alertes(user, password, since), geo
    )


def _source_adzuna(app_id: str, app_key: str) -> Source:
    # Client distinct : la clé LBA ne doit pas partir vers Adzuna, ni l'inverse.
    http = httpx.Client()
    return lambda config, now: adzuna.collecter(config, http, now, app_id, app_key)


def _run(mode: str, dry_run: bool, secrets: Secrets) -> int:
    migrer(secrets.database_url)  # idempotent : un premier run ne plante pas sur une base vide
    config = load_config(CONFIG)
    # La clé LBA voyage dans l'en-tête du client ; absente, la source est ignorée.
    cle = {"Authorization": f"Bearer {secrets.lba_api_key}"} if secrets.lba_api_key else {}
    http = httpx.Client(headers=cle)
    api = None
    if not dry_run and secrets.telegram_bot_token and secrets.telegram_chat_id:
        api = TelegramAPI(secrets.telegram_bot_token, httpx.Client(), chat_id=secrets.telegram_chat_id)
    sources = {nom: _lier(f, http) for nom, f in SOURCES.items()}
    if secrets.gmail_user and secrets.gmail_app_password:
        sources["email"] = _source_email(secrets.gmail_user, secrets.gmail_app_password)
    sources_stage = {}
    if secrets.adzuna_app_id and secrets.adzuna_app_key:
        sources_stage["adzuna"] = _source_adzuna(secrets.adzuna_app_id, secrets.adzuna_app_key)
    with Session(make_engine(secrets.database_url)) as session:
        deps = Deps(
            session,
            config,
            sources,
            OllamaScorer(config.llm, httpx.Client()),
            api,
            sources_stage=sources_stage,
        )
        bilan = executer(mode, deps, datetime.now(UTC))
    print(
        f"Collectées {bilan.collectees} · retenues {bilan.retenues} · notées {bilan.scorees} · "
        f"notifiées {bilan.notifiees}" + (" (dry-run : aucun envoi)" if dry_run else "")
    )
    for e in bilan.erreurs:
        print(f"Erreur : {e}")
    return 0 if bilan.ok else 1


def _bot(secrets: Secrets) -> int:
    if not secrets.telegram_bot_token:
        print("TELEGRAM_BOT_TOKEN absent du .env : crée le bot avec @BotFather.")
        return 1
    if not secrets.telegram_chat_id:
        print("TELEGRAM_CHAT_ID absent du .env : lance d'abord setup-telegram.")
        return 1
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    for bruyant in ("httpx", "httpcore"):
        logging.getLogger(bruyant).setLevel(logging.WARNING)  # httpx journalise les URL, donc le jeton
    migrer(secrets.database_url)
    api = TelegramAPI(secrets.telegram_bot_token, httpx.Client(), chat_id=secrets.telegram_chat_id)
    config = load_config(CONFIG)
    deposer = None
    if secrets.gmail_user and secrets.gmail_app_password:
        user, mdp = secrets.gmail_user, secrets.gmail_app_password

        def deposer(sujet: str, corps: str, pieces: Sequence[Piece]) -> None:
            creer_brouillon(user, mdp, sujet, corps, pieces=pieces)

    with Session(make_engine(secrets.database_url)) as session:
        boucle(
            BotDeps(
                api, session, config, secrets.telegram_chat_id, lambda: datetime.now(UTC),
                redacteur=Redacteur(config.llm, httpx.Client()), deposer=deposer,
                dossier_lettres=Path(secrets.lettres_dir) if secrets.lettres_dir else DOSSIER_LETTRES,
            )
        )  # fmt: skip
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="denicheur")
    sub = parser.add_subparsers(dest="commande", required=True)
    for nom in (*COMMANDES, "init-db", "setup-telegram"):
        sub.add_parser(nom)
    run = sub.add_parser("run")
    run.add_argument("--mode", choices=MODES, default="auto")
    run.add_argument("--dry-run", action="store_true", help="aucun message Telegram")
    sub.add_parser("bot")
    sub.add_parser("digest").add_argument("--test", action="store_true", help="envoie une offre factice")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(
            encoding="utf-8"
        )  # logs lisibles quand la sortie est redirigée vers un fichier
    load_dotenv()
    secrets = load_secrets()
    if args.commande == "run":
        return _run(args.mode, args.dry_run, secrets)
    if args.commande == "init-db":
        migrer(secrets.database_url)
        print("Base initialisée.")
        return 0
    if args.commande == "bot":
        return _bot(secrets)
    if args.commande in ("setup-telegram", "digest"):
        if not secrets.telegram_bot_token:
            print("TELEGRAM_BOT_TOKEN absent du .env : crée le bot avec @BotFather.")
            return 1
        if args.commande == "digest" and not secrets.telegram_chat_id:
            print("TELEGRAM_CHAT_ID absent du .env : lance d'abord setup-telegram.")
            return 1
        api = TelegramAPI(secrets.telegram_bot_token, httpx.Client(), chat_id=secrets.telegram_chat_id)
        try:
            if args.commande == "setup-telegram":
                return _setup_telegram(api)
            if args.test:
                envoyer_test(api)
            else:
                with Session(make_engine(secrets.database_url)) as session:
                    envoyer_digest(session, api, load_config(CONFIG), datetime.now(UTC))
        except TelegramError as e:
            print(e)
            return 1
        return 0
    print(f"{args.commande} : non implémenté")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
