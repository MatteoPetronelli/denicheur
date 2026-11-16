from collections.abc import Callable
from datetime import datetime

import httpx

from denicheur.config import Config
from denicheur.models import Offre
from denicheur.sources import la_bonne_alternance

SOURCES: dict[str, Callable[[Config, httpx.Client, datetime], list[Offre]]] = {
    "lba": la_bonne_alternance.collecter,
}
