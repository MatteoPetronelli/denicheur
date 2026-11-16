"""Heures de Paris : le Planificateur de tâches tourne sur l'heure locale, la base en UTC."""

from datetime import datetime, time
from zoneinfo import ZoneInfo

PARIS = ZoneInfo("Europe/Paris")


def paris_now(now: datetime) -> datetime:
    return now.astimezone(PARIS)


def _heure(texte: str) -> time:
    return time.fromisoformat(texte)


def is_daytime(now: datetime, debut: str = "08:00", fin: str = "20:00") -> bool:
    """Vrai de `debut` (inclus) à `fin` (exclue), heure de Paris."""
    return _heure(debut) <= paris_now(now).time() < _heure(fin)


def heure_atteinte(now: datetime, heure: str) -> bool:
    return paris_now(now).time() >= _heure(heure)
