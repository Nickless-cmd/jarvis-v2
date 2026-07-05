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
