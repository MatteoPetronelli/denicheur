import argparse
from datetime import UTC, datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from denicheur.config import load_config, load_secrets
from denicheur.db.base import make_engine, migrer
from denicheur.telegram.api import TelegramAPI, TelegramError
from denicheur.telegram.digest import envoyer_digest, envoyer_test

COMMANDES = ("run", "stats")
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="denicheur")
    sub = parser.add_subparsers(dest="commande", required=True)
    for nom in (*COMMANDES, "init-db", "setup-telegram"):
        sub.add_parser(nom)
    sub.add_parser("digest").add_argument("--test", action="store_true", help="envoie une offre factice")
    args = parser.parse_args(argv)
    load_dotenv()
    secrets = load_secrets()
    if args.commande == "init-db":
        migrer(secrets.database_url)
        print("Base initialisée.")
        return 0
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
