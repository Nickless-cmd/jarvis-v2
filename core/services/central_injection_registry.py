"""Central-styret injektions-register (ændrings-drevet indre liv, spec 2026-07-05).

Centralen vedligeholder indre-livs-sektioner i BAGGRUNDEN: en refresh-motor (cadence,
runtime-proces) genberegner kun BESKIDTE enheder og skriver deres tekst durabelt.
Prompt-assembly (api-proces) LÆSER den cachede tekst — komponerer aldrig. Ét sted alt
flyder igennem: Centralen afgør hvornår en sektion har ændret sig materielt.

Self-safe: kaster ALDRIG. read_injection falder tilbage til tom streng.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

_CACHE_PREFIX = "injection:cache:"   # + key → {"text", "composed_at", "source_snapshot"}
_LIVE_PREFIX = "injection:live:"     # + key → bool (rollback-flag; default False = direkte build)


@dataclass
class InjectionUnit:
    key: str
    source_nerves: tuple[str, ...]
    threshold: float
    max_age_s: float
    compose_fn: Callable[[], str]
    priority: int = 50


_REGISTRY: dict[str, InjectionUnit] = {}


def _kv_get(key: str, default: Any) -> Any:
    try:
        from core.runtime.db_core import get_runtime_state_value
        v = get_runtime_state_value(key, default)
        return v if v is not None else default
    except Exception:
        return default


def _kv_set(key: str, value: Any) -> None:
    try:
        from core.runtime.db_core import set_runtime_state_value
        set_runtime_state_value(key, value)
    except Exception:
        pass


def register(unit: InjectionUnit) -> None:
    _REGISTRY[unit.key] = unit


def registered_keys() -> list[str]:
    return list(_REGISTRY)


def read_injection(key: str) -> str:
    """Hot-path (api-proces): læs den cachede injektions-tekst. ALDRIG et compose-kald.
    Tom streng hvis aldrig komponeret → assembly blokerer aldrig på et indre-livs-kald."""
    blob = _kv_get(_CACHE_PREFIX + key, {})
    if not isinstance(blob, dict):
        return ""
    return str(blob.get("text") or "")


def _nerve_latest(nerve: str) -> float | None:
    """Seneste værdi for 'cluster:nerve' fra central_timeseries. None hvis ukendt.
    Kører i runtime-procesen hvor de kognitive nerver produceres."""
    try:
        from core.services import central_timeseries as ts
        entry = ts.snapshot().get(nerve) or {}
        v = entry.get("latest")
        return float(v) if v is not None else None
    except Exception:
        return None


def is_dirty(unit: InjectionUnit, now: float) -> bool:
    """Beskidt hvis: aldrig komponeret, over max-alder, ELLER en kilde-nerve flyttet > tærskel."""
    blob = _kv_get(_CACHE_PREFIX + unit.key, {})
    if not isinstance(blob, dict) or not blob.get("composed_at"):
        return True
    try:
        if now - float(blob["composed_at"]) > unit.max_age_s:
            return True
    except Exception:
        return True
    snap = blob.get("source_snapshot") or {}
    for nerve in unit.source_nerves:
        cur = _nerve_latest(nerve)
        if cur is None:
            continue
        prev = snap.get(nerve)
        if prev is None:
            return True
        try:
            if abs(cur - float(prev)) > unit.threshold:
                return True
        except Exception:
            return True
    return False


def refresh_unit(unit: InjectionUnit, now: float) -> None:
    """Genberegn ÉN enhed (det tunge LLM/subsystem-kald — OFF hot-path) og skriv durabelt."""
    text = unit.compose_fn() or ""
    snap = {}
    for nerve in unit.source_nerves:
        v = _nerve_latest(nerve)
        if v is not None:
            snap[nerve] = v
    _kv_set(_CACHE_PREFIX + unit.key, {
        "text": str(text), "composed_at": float(now), "source_snapshot": snap,
    })


def refresh_dirty(now: float | None = None) -> int:
    """Kaldes fra Centralens cadence: refresh alle beskidte enheder. Self-safe pr. enhed.
    Returnerer antal genberegnede (til observabilitet)."""
    if now is None:
        now = time.time()
    n = 0
    for unit in sorted(_REGISTRY.values(), key=lambda u: u.priority):
        try:
            if is_dirty(unit, now):
                refresh_unit(unit, now)
                n += 1
        except Exception:
            continue
    return n
