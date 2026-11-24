"""Ét sted at bogføre et Ollama-kald — så ingen sti kan glemme det.

HVORFOR (målt 24/11-2026). ``GET https://ollama.com/api/usage`` med vores egen
nøgle svarede **$34,27 og 19.472 kald** for de sidste syv dage. Den levende
``costs``-tabel havde 1.055 ollama-rækker og $3,65. Dækningen var 3-8% **hver
enkelt dag** — ikke en enkelt spike — og token-dækningen var lavere end
kald-dækningen, så de manglende kald bar de STØRRE prompts.

Årsagen var ikke en manglende pris-tabel: ``record_cost`` beregner selv prisen
fra ``OLLAMA_PRICING`` når kalderen ikke giver en. Det var KALDET der manglede.
Målt på filniveau: ni filer sender rigtige Ollama-kald, og kun én af dem
(`prompt_relevance_backend`) kaldte `record_cost`. Resten returnerede deres
token-tal til en kalder der ikke gjorde noget med dem — eller til ingenting.

To ting er værd at vide om prisen, for de er ikke det samme som en regning:

* Ollamas ``usage_usd`` er en **kvote-måler**, ikke en faktura. Bjørn har en
  pro-plan med en månedlig grænse (mail 24/11-2026: «You've reached 90% of your
  monthly limit»), ikke pay-as-you-go.
* Vores ``OLLAMA_PRICING`` giver **$60,82** for de samme 919,7 mio tokens som
  Ollama selv måler til $34,27 — altså 1,8x for højt. At lukke bogførings-hullet
  gør regnskabet mere KOMPLET, men ikke mere sandt i kroner. Derfor findes
  :func:`kvote_reference` nedenfor: den henter Ollamas eget tal, så kvote-forbrug
  kan følges uden om vores pris-tabel.
"""

from __future__ import annotations

import json
import logging
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

#: Ollamas eget forbrugs-endpoint. Der er INTET saldo-felt — kun forbrug
#: (målt 6/11-2026; `/api/me`, `/api/account` og `/api/billing` findes ikke).
USAGE_URL = "https://ollama.com/api/usage"


def bogfoer_ollama_kald(
    *,
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_hit_tokens: int = 0,
    cache_miss_tokens: int = 0,
    lane: str,
) -> float:
    """Bogfør ét Ollama-kald i hovedbogen og returnér den beregnede pris.

    Fejler aldrig højt: en fejl i regnskabet må ikke vælte det arbejde der
    betalte for kaldet. Men den forsvinder heller ikke — den logges, og et nul
    kan ses i den lane der kaldte.
    """
    try:
        from core.costing.ledger import record_cost
        from core.services.llm_pricing import compute_cost_usd

        pris = float(
            compute_cost_usd(
                provider,
                model,
                cache_hit_tokens=cache_hit_tokens,
                cache_miss_tokens=cache_miss_tokens,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
        )
        try:
            from core.services.session_context_resolve import aktivt_run_id

            run_id = aktivt_run_id("")
        except Exception:
            run_id = ""
        record_cost(
            lane=lane,
            provider=provider,
            model=model,
            input_tokens=int(input_tokens or 0),
            output_tokens=int(output_tokens or 0),
            cache_hit_tokens=int(cache_hit_tokens or 0),
            cache_miss_tokens=int(cache_miss_tokens or 0),
            cost_usd=pris,
            run_id=run_id,
        )
        return pris
    except Exception:
        logger.debug(
            "ollama-usage: kunne ikke bogfoere %s/%s (lane=%s)",
            provider,
            model,
            lane,
            exc_info=True,
        )
        return 0.0


def kvote_reference(*, timeout: float = 20.0) -> dict[str, Any] | None:
    """Ollamas EGEN forbrugsmåling — det tal der styrer pro-planens 90%-grænse.

    Returnerer ``None`` når den ikke kunne hentes, aldrig et gæt. Brugen er at
    holde vores eget regnskab op mod den målestok brugeren faktisk rammer, i
    stedet for at gætte kvote ud fra vores pris-tabel (som overestimerer 1,8x).
    """
    try:
        from core.runtime.secrets import read_runtime_key

        noegle = read_runtime_key("ollama_api_key")
        if not noegle:
            return None
        req = urllib.request.Request(
            USAGE_URL,
            headers={
                "Authorization": f"Bearer {noegle}",
                "User-Agent": "jarvis-ollama-usage",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raa = json.loads(resp.read().decode("utf-8"))
        totaler = raa.get("totals") or {}
        return {
            "range": raa.get("range"),
            "fra": raa.get("from"),
            "til": raa.get("until"),
            "kald": int(totaler.get("request_count") or 0),
            "usage_usd": float(totaler.get("usage_usd") or 0.0),
            "input_tokens": int(totaler.get("input_tokens") or 0),
            "cached_input_tokens": int(totaler.get("cached_input_tokens") or 0),
            "output_tokens": int(totaler.get("output_tokens") or 0),
            "buckets": raa.get("buckets") or [],
        }
    except Exception:
        logger.debug("ollama-usage: kvote-reference kunne ikke hentes", exc_info=True)
        return None
