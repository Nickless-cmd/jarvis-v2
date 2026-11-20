"""Streaming og perceived performance — fra skøn til måling.

## Hvorfor den findes

MÅLT 20/11-2026: domænet stod på 42 % gennem 1.027 vektorer. Fire distinkte
værdier, alle sat af modellens eget skøn i `personality_vector`. Ingen måling
lå bag — og det kunne den ikke være, fordi `svar_tempo` kastede sit tal væk
(se `core/runtime/db_tempo.py`).

## Hvad der måles

**Median TTFT** over de seneste målinger: hvor længe sidder Bjørn og kigger på
ingenting, før det første tegn kommer. Det er den ventetid «perceived
performance» beskriver.

Total tur-tid måles ikke her. Den er persisteret i `visible_runs`, men måler
hele agent-loopet inklusive værktøjskald: målt 20/11-2026 var medianen for
synlige ture 98,1 sekunder. Det er et rigtigt tal, men det er ikke den ventetid
man mærker før svaret begynder.

## Skalaen er vedtaget, ikke målt

Tallene er målinger. Oversættelsen fra millisekunder til 0-1 er en vedtaget
skala, og den står her for at kunne diskuteres — ikke for at se ud som om den
er udledt af data. Grænserne følger det Bjørn faktisk kan mærke: under et
sekund føles som straks, over otte sekunder føles som om noget er galt.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

DOMAIN = "streaming og perceived performance"

#: Færre end dette, og medianen er ikke et udsagn om evnen — kun om de få ture
#: der tilfældigvis kørte. Samme tærskel som forsøgs-evalueringen bruger.
_MIN_MAALINGER = 20

#: (øvre graense for median TTFT i ms, confidence). Faldende.
_SKALA: tuple[tuple[float, float], ...] = (
    (1000.0, 0.90),   # under et sekund: føles som straks
    (2000.0, 0.75),
    (4000.0, 0.60),
    (8000.0, 0.45),
    (float("inf"), 0.30),
)


def _median(values: list[float]) -> float:
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2.0


def _percentil(values: list[float], p: float) -> float:
    s = sorted(values)
    if not s:
        return 0.0
    idx = min(len(s) - 1, max(0, int(round(p * (len(s) - 1)))))
    return s[idx]


def _confidence_for(median_ms: float) -> float:
    for graense, conf in _SKALA:
        if median_ms < graense:
            return conf
    return _SKALA[-1][1]


def measure(*, limit: int = 200, write: bool = True) -> dict[str, Any]:
    """Mål streaming-evnen på de faktiske TTFT-målinger.

    Skriver kun når der er nok målinger. Uden historik er svaret «ikke målt» —
    ikke en gættet confidence. Det er hele pointen: et tal uden data bag er
    præcis den fejl denne måler findes for at fjerne.
    """
    from core.runtime import db_tempo

    rows = db_tempo.seneste(limit=limit)
    ttfts = [
        float(r["ttft_ms"])
        for r in rows
        if r.get("ttft_ms") is not None
    ]
    n = len(ttfts)
    if n < _MIN_MAALINGER:
        return {
            "measured": False,
            "n": n,
            "required": _MIN_MAALINGER,
            "reason": (
                f"kun {n} TTFT-målinger — der kræves {_MIN_MAALINGER} "
                "for at medianen siger noget om evnen"
            ),
            "written": None,
        }

    median_ms = round(_median(ttfts), 1)
    p90_ms = round(_percentil(ttfts, 0.90), 1)
    tok = [float(r["tok_per_sek"]) for r in rows if r.get("tok_per_sek") is not None]
    confidence = _confidence_for(median_ms)

    written = None
    if write:
        try:
            from core.services.capability_measurement import set_domain_confidence

            written = set_domain_confidence(
                DOMAIN,
                confidence,
                evidence=(
                    f"median TTFT {median_ms:.0f} ms (p90 {p90_ms:.0f} ms) "
                    f"over {n} målte ture"
                ),
            )
        except Exception as exc:  # noqa: BLE001
            # Målingen er stadig gyldig selv om skrivningen fejler; den
            # returneres, så kalderen kan se at den ikke landede.
            logger.warning("streaming: kunne ikke skrive confidence: %s", exc)

    return {
        "measured": True,
        "n": n,
        "median_ttft_ms": median_ms,
        "p90_ttft_ms": p90_ms,
        "median_tok_per_sek": round(_median(tok), 1) if tok else None,
        "confidence": confidence,
        "written": written,
    }


__all__ = ["measure", "DOMAIN"]
