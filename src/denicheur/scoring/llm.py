from datetime import date
from typing import NamedTuple, Protocol

import httpx
from pydantic import ValidationError

from denicheur.config import LLMConfig
from denicheur.models import Offre, ScoreLLM
from denicheur.scoring.prompts import system_scoring, user_message


class Usage(NamedTuple):
    prompt_tokens: int
    output_tokens: int
    duree_s: float


class OllamaIndisponible(Exception):
    """Connexion refusée : Ollama n'est pas lancé."""


class ScoreInvalide(Exception):
    """Réponse inutilisable (JSON invalide, score hors bornes, erreur HTTP, délai dépassé)."""


class Scorer(Protocol):
    def scorer(self, offre: Offre, today: date) -> tuple[ScoreLLM, Usage]: ...


class OllamaScorer:
    def __init__(self, llm: LLMConfig, http: httpx.Client) -> None:
        self.llm, self.http = llm, http

    def scorer(self, offre: Offre, today: date) -> tuple[ScoreLLM, Usage]:
        c = self.llm.scoring  # modèle et options viennent de la config, jamais surchargés ici
        body = {
            "model": c.modele,
            "messages": [
                {"role": "system", "content": system_scoring()},
                {"role": "user", "content": user_message(offre, today)},
            ],
            "format": ScoreLLM.model_json_schema(),
            "stream": False,
            "keep_alive": "10m",
            "options": {"temperature": c.temperature, "seed": 42, "num_ctx": c.num_ctx},
        }
        try:
            r = self.http.post(f"{self.llm.url}/api/chat", json=body, timeout=c.timeout_s)
            r.raise_for_status()
            data = r.json()
            score = ScoreLLM.model_validate_json(data["message"]["content"])
            usage = Usage(data["prompt_eval_count"], data["eval_count"], data["total_duration"] / 1e9)
        except httpx.ConnectError as e:
            raise OllamaIndisponible(str(e)) from e
        except (httpx.HTTPError, ValidationError, KeyError, ValueError) as e:
            raise ScoreInvalide(f"{type(e).__name__}: {e}") from e
        return score, usage
