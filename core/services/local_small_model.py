"""Ét-ords-spoergsmaal til den lille lokale model paa Jarvis' eget kort.

Udskilt 7/9-2026 da kalder nummer to kom til (``local_intent_gate`` og
``smith_noise_veto``). Begge stiller samme slags spoergsmaal: en kort tekst
ind, ét ord ud, og et svar der aldrig maa vaere vaerd at vente paa.

Modellen ligger residens i CT105's VRAM (qwen3:4b, 5,37 af 8 GB, keep_alive
uendeligt) paa et kort med 0 % udnyttelse. Maalt: 0,17-0,19 s pr. kald.

## Hvorfor lokalt frem for cheap lane

Ikke kvalitet — **fejlretning**. Begge kaldere sidder taet paa Jarvis' prompt
og hans staaende direktiver. En udbyder der er nede har to gange leveret sin
kvotefejl videre som INDHOLD (``provider_error_in_self_anchor``; explore-fundet
der viste sig at vaere en fejlbesked). En lokal model der er nede leverer
``None``, og kalderen bestemmer selv hvad tavshed betyder.

## Hvorfor deadlinen er saa stram

Ollama-kald KOEER 28-91 s naar ollama er optaget — dokumenteret som selve
cut-off-roden i ``prompt_contract._timed_result``. Standarden her giver otte
gange luft over det maalte kald og fejler til ``None``.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

MODEL = "qwen3:4b-instruct-2507-q4_K_M"
STANDARD_TIMEOUT_S = 1.5


def base_url() -> str:
    try:
        from core.services.semantic_memory import _ollama_base_url
        return (_ollama_base_url() or "").rstrip("/") or "http://127.0.0.1:11434"
    except Exception:
        return "http://127.0.0.1:11434"


def spoerg_et_ord(
    system: str, bruger: str, *, timeout_s: float = STANDARD_TIMEOUT_S,
) -> str | None:
    """Foerste HELE ord af modellens svar, med STORE bogstaver. ``None`` = intet svar.

    ``None`` daekker alt: modellen er nede, den koeer, den svarer uforstaaeligt.
    Kalderen afgoer hvad det betyder — de to nuvaerende kaldere laeser det
    modsat, og det er med vilje (se deres respektive moduler).

    Foerste ORD, ikke praefiks: «JAVEL» er ikke et ja, og begge kaldere fejler
    i en retning hvor et fejllaest ord koster noget.
    """
    system = (system or "").strip()
    bruger = (bruger or "").strip()
    if not system or not bruger:
        return None

    krop = json.dumps({
        "model": MODEL,
        "stream": False,
        "options": {"temperature": 0, "num_predict": 4},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": bruger[:1200]},
        ],
    }).encode()

    try:
        anmodning = urllib.request.Request(  # noqa: S310 - fast lokal URL
            f"{base_url()}/api/chat", krop, {"Content-Type": "application/json"})
        with urllib.request.urlopen(anmodning, timeout=timeout_s) as svar:  # noqa: S310
            data = json.loads(svar.read())
        tekst = str((data.get("message") or {}).get("content") or "").strip().upper()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        logger.debug("local_small_model: naaede ikke modellen (%s)", exc)
        return None
    except Exception as exc:
        logger.debug("local_small_model: uventet svar: %s", exc)
        return None

    foerste = re.match(r"[A-ZÆØÅ]+", tekst)
    return foerste.group(0) if foerste else None
