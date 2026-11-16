import time
from collections.abc import Callable
from typing import Any

import httpx

BASE = "https://api.telegram.org"


class TelegramError(Exception):
    """Message volontairement sans URL : l'URL de l'API contient le jeton du bot."""


class TelegramAPI:
    """Client lié à un seul chat : aucune méthode d'envoi n'accepte un `chat_id`."""

    def __init__(
        self, token: str, http: httpx.Client, *, chat_id: str | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:  # fmt: skip
        self._token, self._http, self._chat_id, self._sleep = token, http, chat_id, sleep
        self._deja_envoye = False

    def _appel(self, methode: str, **donnees: Any) -> Any:
        try:
            r = self._http.post(f"{BASE}/bot{self._token}/{methode}", json=donnees, timeout=60)
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise TelegramError(f"Telegram {methode} : HTTP {e.response.status_code}") from None
        except httpx.HTTPError as e:
            raise TelegramError(f"Telegram {methode} : {type(e).__name__}") from None
        return r.json()["result"]

    def _chat(self) -> str:
        if self._chat_id is None:
            raise TelegramError("TELEGRAM_CHAT_ID absent : lance d'abord setup-telegram")
        return self._chat_id

    def send_message(self, texte: str, reply_markup: dict[str, Any] | None = None) -> Any:
        chat = self._chat()
        if self._deja_envoye:
            self._sleep(1)  # limite de débit de Telegram
        self._deja_envoye = True
        donnees: dict[str, Any] = {"chat_id": chat, "text": texte, "parse_mode": "HTML"}
        if reply_markup:
            donnees["reply_markup"] = reply_markup
        return self._appel("sendMessage", **donnees)

    def answer_callback(self, callback_id: str, texte: str | None = None) -> Any:
        return self._appel("answerCallbackQuery", callback_query_id=callback_id, text=texte)

    def edit_keyboard(self, message_id: int, reply_markup: dict[str, Any]) -> Any:
        return self._appel(
            "editMessageReplyMarkup", chat_id=self._chat(), message_id=message_id, reply_markup=reply_markup
        )

    def delete_webhook(self) -> Any:
        return self._appel("deleteWebhook")

    def get_updates(self, offset: int | None = None, timeout: int = 0) -> list[dict[str, Any]]:
        return self._appel("getUpdates", offset=offset, timeout=timeout)
