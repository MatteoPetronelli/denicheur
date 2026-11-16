import time
from collections.abc import Callable
from typing import Any

import httpx


def get_json(
    client: httpx.Client,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    max_retries: int = 4,
    sleep: Callable[[float], None] = time.sleep,
) -> Any:
    """GET + JSON. 429 / 5xx / timeout : retry (max_retries tentatives au total) ; autre 4xx : levé."""
    for tentative in range(max_retries):
        derniere = tentative == max_retries - 1
        try:
            r = client.get(url, params=params, headers=headers)
        except httpx.TimeoutException:
            if derniere:
                raise
            sleep(2**tentative)
            continue
        if r.status_code == 429 or r.status_code >= 500:
            if derniere:
                r.raise_for_status()
            sleep(int(r.headers.get("Retry-After") or 2**tentative))
            continue
        r.raise_for_status()
        return r.json()
    raise ValueError("max_retries doit être >= 1")
