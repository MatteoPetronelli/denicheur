import httpx
import pytest

from denicheur.http import get_json


def _client(reponses):
    appels = []

    def handler(request):
        appels.append(request)
        r = reponses[min(len(appels) - 1, len(reponses) - 1)]
        if isinstance(r, Exception):
            raise r
        return r

    return httpx.Client(transport=httpx.MockTransport(handler)), appels


def test_429_puis_succes_attend_retry_after():
    client, appels = _client(
        [httpx.Response(429, headers={"Retry-After": "7"}), httpx.Response(200, json={"ok": 1})]
    )
    attentes = []
    assert get_json(client, "http://x", sleep=attentes.append) == {"ok": 1}
    assert attentes == [7] and len(appels) == 2


def test_429_sans_retry_after_backoff_exponentiel():
    client, _ = _client([httpx.Response(429), httpx.Response(429), httpx.Response(200, json=[])])
    attentes = []
    get_json(client, "http://x", sleep=attentes.append)
    assert attentes == [1, 2]


def test_401_sans_nouvelle_tentative():
    client, appels = _client([httpx.Response(401)])
    with pytest.raises(httpx.HTTPStatusError):
        get_json(client, "http://x", sleep=lambda s: None)
    assert len(appels) == 1


def test_503_epuise_les_tentatives():
    client, appels = _client([httpx.Response(503)])
    with pytest.raises(httpx.HTTPStatusError):
        get_json(client, "http://x", max_retries=3, sleep=lambda s: None)
    assert len(appels) == 3


def test_timeout_reessaye():
    client, appels = _client([httpx.ReadTimeout("t"), httpx.Response(200, json={"a": 1})])
    assert get_json(client, "http://x", sleep=lambda s: None) == {"a": 1}
    assert len(appels) == 2
