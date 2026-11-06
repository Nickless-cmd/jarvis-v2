"""Ollama-lanens tilstand — målt, aldrig gættet.

## Hvad der er MÅLT (6/11-2026)

* ``GET https://ollama.com/api/usage`` (Bearer ``ollama_api_key``) svarer 200
  med FORBRUG (``totals.usage_usd``, request_count, tokens, dagsbuckets).
  Der er INTET saldo-felt. ``/api/me``, ``/api/account`` og ``/api/billing``
  findes ikke (405/404/404). Saldoen kan altså ikke aflæses FØR et kald.
* ``/api/tags`` på den lokale daemon svarer 200 uanset konto — ikke et signal.
* Ægte kald med forkert nøgle: HTTP 401 ``{"error":"Unauthorized"}``.
* Hændelsen 6/11 kl. 05:00-05:35: ollamas journal viser HTTP 200 på ALLE
  ``POST /api/chat`` mellem 05:08 og 05:30, og ingen ikke-200 overhovedet.
  Det var altså IKKE en tom ollama-konto der holdt de fem kørsler tilbage.
  Hvad et kald returnerer ved reelt tom saldo er IKKE målt — kontoen kan ikke
  tømmes for at prøve, og ingen log indeholder et sådant svar.

## Konsekvens for designet

Der gættes ikke på en fejlkode. Det eneste ærlige signal er et ægte
1-token-kald gennem den sti lanen bruger:

* HTTP 200                → ``healthy``
* HTTP-fejl (alle andre)  → ``blocked``, med status og svartekst VERBATIM.
  Hvilken betydning koden har (betaling, rate-limit, nøgle) afgør et menneske
  ud fra den rå tekst; vi påstår ikke «tom saldo».
* transport-/tidsfejl     → ``unknown`` (fail-open: uvidenhed blokerer intet).

Proben bruges kun mens en kørsel ALLEREDE venter, og resultatet caches.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable

CACHE_TTL_SECONDS = 60.0
HTTP_TIMEOUT_SECONDS = 20.0
DEFAULT_BASE_URL = "http://127.0.0.1:11434"
BODY_LIMIT = 200

HEALTHY = "healthy"
BLOCKED = "blocked"
UNKNOWN = "unknown"


@dataclass(frozen=True)
class OllamaReading:
    state: str  # healthy | blocked | unknown
    status: int = 0
    detail: str = ""  # rå svartekst / fejltype, uden fortolkning

    @property
    def blocked(self) -> bool:
        return self.state == BLOCKED


_cache: tuple[float, OllamaReading] | None = None


def reset_cache() -> None:
    global _cache
    _cache = None


def _post(base_url: str, model: str, timeout: float) -> OllamaReading:
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": "ping"}],
        "stream": False,
        "options": {"num_predict": 1},
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/chat", data=body,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return OllamaReading(HEALTHY, int(response.status))
    except urllib.error.HTTPError as exc:
        try:
            text = exc.read().decode("utf-8", errors="replace")[:BODY_LIMIT]
        except Exception:  # noqa: BLE001
            text = ""
        return OllamaReading(BLOCKED, int(exc.code), text or str(exc.reason))
    except Exception as exc:  # noqa: BLE001 — uvidenhed er ikke en blokering
        return OllamaReading(UNKNOWN, 0, type(exc).__name__)


def probe_ollama(
    model: str,
    *,
    base_url: str = DEFAULT_BASE_URL,
    timeout: float = HTTP_TIMEOUT_SECONDS,
    prober: Callable[[str, str, float], OllamaReading] | None = None,
    now: Callable[[], float] = time.monotonic,
) -> OllamaReading:
    """Ægte 1-token-kald, cachet i :data:`CACHE_TTL_SECONDS`."""
    global _cache
    current = now()
    if _cache is not None and current - _cache[0] < CACHE_TTL_SECONDS:
        return _cache[1]
    reading = (prober or _post)(base_url, model, timeout)
    _cache = (current, reading)
    return reading


def render_reason(reading: OllamaReading) -> str:
    return f"ollama-lanen afviste et prøvekald: HTTP {reading.status} {reading.detail}".strip()
