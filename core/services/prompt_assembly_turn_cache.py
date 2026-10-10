"""Small process-local cache for reusing one prompt assembly within a turn.

The cache deliberately has no lock or single-flight behavior. Concurrent
misses remain independent builds, preserving the behavior of the cache that
previously lived inside :mod:`prompt_contract`.
"""
from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Literal


TTL_S = 180.0
MAX_ENTRIES_BEFORE_CLEAR = 64
_CACHE: dict[tuple, tuple[float, Any]] = {}


@dataclass(frozen=True, slots=True)
class CacheLookup:
    outcome: Literal["hit", "miss", "unsafe_no_key", "expired"]
    value: Any = None
    age_ms: int | None = None


def lookup(key: tuple | None, *, now: float | None = None) -> CacheLookup:
    if key is None:
        return CacheLookup("unsafe_no_key")
    checked_at = time.monotonic() if now is None else now
    item = _CACHE.get(key)
    if item is None:
        return CacheLookup("miss")
    age_ms = max(0, round((checked_at - item[0]) * 1000))
    if checked_at - item[0] >= TTL_S:
        return CacheLookup("expired", age_ms=age_ms)
    return CacheLookup("hit", value=item[1], age_ms=age_ms)


def store(key: tuple, value: Any, *, now: float | None = None) -> None:
    stored_at = time.monotonic() if now is None else now
    if len(_CACHE) > MAX_ENTRIES_BEFORE_CLEAR:
        _CACHE.clear()
    _CACHE[key] = (stored_at, value)


def clear() -> None:
    _CACHE.clear()
