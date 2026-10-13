"""Proaktiv kvote-rotation (spec §5.5 Fund 3): flyt last væk FØR 429.

Læser forbrug fra SQLite cheap_provider_invocations, beregner brug/limit-fraktion.
>=80% -> de-vægt (mindre sandsynlig at vælges); >=95% -> skip proaktivt."""
from __future__ import annotations

import time

_DEWEIGHT_AT = 0.80
_SKIP_AT = 0.95

# 2026-10-12: TTL-cache pr. provider. Målt: ét central_route.route(lane="cheap")
# kaldte _usage_fraction 361 gange, og hver beregning kørte sin egen COUNT(*)
# mod cheap_provider_invocations — 343 af de 2.548 SQLite-kald pr. route().
# headroom_ok() og headroom_weight() spørger hver især om SAMME provider i samme
# rangering, så det andet kald var altid et rent genkald af det første.
#
# 30 s er valgt fordi kvote-rotation er en blød, proaktiv foranstaltning (flyt
# last FØR 429), ikke en hård gate: en halvt minut gammel brøk flytter stadig
# lasten væk i god tid. En hård gate ville kræve frisk data.
_USAGE_TTL_SECONDS = 30.0
_USAGE_CACHE: dict[str, tuple[float, float]] = {}


def _clear_usage_cache() -> None:
    """Tøm brøk-cachen (tests, og efter en tvungen kvote-nulstilling)."""
    _USAGE_CACHE.clear()


def _usage_fraction(provider: str) -> float:
    """(brug/daily_limit) i seneste 24t-vindue. 0.0 ved fejl/ingen limit."""
    _now = time.monotonic()
    _hit = _USAGE_CACHE.get(provider)
    if _hit is not None and _hit[0] > _now:
        return _hit[1]
    try:
        from datetime import datetime, timedelta, UTC
        from core.runtime.db_cheap_provider import count_cheap_provider_invocations
        from core.services.cheap_provider_runtime_adapters import CHEAP_PROVIDER_DEFAULTS
        cfg = CHEAP_PROVIDER_DEFAULTS.get(provider) or {}
        daily = cfg.get("daily_limit")
        if not daily:
            return 0.0
        since = (datetime.now(UTC) - timedelta(hours=24)).isoformat()
        used = int(count_cheap_provider_invocations(
            provider=provider, lane="cheap", since=since) or 0)
        fraction = min(1.0, used / float(daily))
    except Exception:
        # Fejlstien caches IKKE: en transient DB-fejl må ikke fryse provideren
        # som «fuld headroom» i 30 sekunder.
        return 0.0
    _USAGE_CACHE[provider] = (_now + _USAGE_TTL_SECONDS, fraction)
    return fraction


def headroom_ok(provider: str) -> bool:
    """False = proaktivt skip (>=95% brugt)."""
    return _usage_fraction(provider) < _SKIP_AT


def headroom_weight(provider: str) -> float:
    """1.0 = fuld headroom; falder lineært mod 0.1 mellem 80% og 95%."""
    u = _usage_fraction(provider)
    if u < _DEWEIGHT_AT:
        return 1.0
    span = max(_SKIP_AT - _DEWEIGHT_AT, 1e-6)
    return max(0.1, 1.0 - (u - _DEWEIGHT_AT) / span * 0.9)
