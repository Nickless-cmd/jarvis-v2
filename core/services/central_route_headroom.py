"""Proaktiv kvote-rotation (spec §5.5 Fund 3): flyt last væk FØR 429.

Læser forbrug fra SQLite cheap_provider_invocations, beregner brug/limit-fraktion.
>=80% -> de-vægt (mindre sandsynlig at vælges); >=95% -> skip proaktivt."""
from __future__ import annotations

_DEWEIGHT_AT = 0.80
_SKIP_AT = 0.95


def _usage_fraction(provider: str) -> float:
    """(brug/daily_limit) i seneste 24t-vindue. 0.0 ved fejl/ingen limit."""
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
        return min(1.0, used / float(daily))
    except Exception:
        return 0.0


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
