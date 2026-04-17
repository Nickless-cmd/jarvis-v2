"""Tick-scoped in-memory cache — lives exactly one heartbeat tick.

Activated by start_tick() at tick start, cleared by end_tick() at tick end.
When inactive (_cache is None), get() returns None and set() is a no-op,
making it safe for non-heartbeat callers to use without guards.
"""
from __future__ import annotations

_cache: dict[str, object] | None = None
_hits: int = 0
_misses: int = 0


def start_tick() -> None:
    """Activate cache for this tick. Resets any previous data."""
    global _cache, _hits, _misses
    _cache = {}
    _hits = 0
    _misses = 0


def end_tick() -> None:
    """Deactivate cache and clear all data."""
    global _cache, _hits, _misses
    _cache = None
    _hits = 0
    _misses = 0


def get(key: str) -> object | None:
    """Return cached value or None. Safe to call when inactive."""
    global _hits, _misses
    if _cache is None:
        return None
    value = _cache.get(key)
    if value is not None:
        _hits += 1
    else:
        _misses += 1
    return value


def set(key: str, value: object) -> None:
    """Store value for this tick. No-op when inactive."""
    if _cache is None:
        return
    _cache[key] = value


def get_tick_cache_stats() -> dict[str, object]:
    """Return hit/miss stats for current tick."""
    return {
        "active": _cache is not None,
        "size": len(_cache) if _cache is not None else 0,
        "hits": _hits,
        "misses": _misses,
    }
