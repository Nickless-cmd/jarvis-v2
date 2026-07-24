"""Recursion guard for autonomous agent dispatch.

An autonomous dispatch that carries a ``can-spawn`` role could fan out into an
unbounded agent tree: each spawned agent spawns more, each dispatch requests
many children, and many such trees run at once. This module bounds that growth
along three independent axes:

- **depth** — how deep a spawn chain may go (``can_spawn``)
- **fan-out** — how many children a single dispatch may request
  (``fanout_allowed``)
- **concurrency** — how many autonomous agents may run at once, tracked in a
  *durable* counter (``try_enter`` / ``exit`` / ``active_count``)

Pure depth/fan-out checks take no state. The concurrency counter is persisted
via runtime-state so it survives process restarts and is shared across
processes. A stale-entry guard reclaims slots whose dispatch crashed without
calling ``exit``, so a dead run never leaks a slot forever.

Self-safe: fail-open on any storage error (never wedge a dispatch on a guard
bug), thresholds tunable at runtime via runtime-state.
"""

from __future__ import annotations

import time

from core.runtime import db as _db

# --- runtime-state keys -----------------------------------------------------
_STATE_ACTIVE = "recursion_guard_active_entries"  # durable list[float] of enter-timestamps
_STATE_MAX_DEPTH = "recursion_guard_max_depth"
_STATE_MAX_FANOUT = "recursion_guard_max_fanout"
_STATE_MAX_CONCURRENT = "recursion_guard_max_concurrent"
_STATE_TTL = "recursion_guard_stale_ttl_s"

# --- defaults ---------------------------------------------------------------
DEFAULT_MAX_DEPTH = 2
DEFAULT_MAX_FANOUT = 8
DEFAULT_MAX_CONCURRENT = 6
DEFAULT_STALE_TTL_S = 600.0


def _tunable_int(key: str, default: int) -> int:
    """Read an int threshold from runtime-state; fall back to ``default``."""
    try:
        raw = _db.get_runtime_state_value(key, default)
        val = int(raw)
        return val if val >= 0 else default
    except Exception:
        return default


def _tunable_float(key: str, default: float) -> float:
    try:
        raw = _db.get_runtime_state_value(key, default)
        val = float(raw)
        return val if val >= 0 else default
    except Exception:
        return default


# --- pure checks ------------------------------------------------------------
def can_spawn(current_depth: int, max_depth: int | None = None) -> bool:
    """True while a spawn chain still has depth budget.

    The ``can-spawn`` role carries a depth budget; each level decrements it.
    Returns False once ``current_depth`` has reached ``max_depth``.
    """
    if max_depth is None:
        max_depth = _tunable_int(_STATE_MAX_DEPTH, DEFAULT_MAX_DEPTH)
    try:
        return int(current_depth) < int(max_depth)
    except Exception:
        return False


def fanout_allowed(requested: int, max_fanout: int | None = None) -> bool:
    """True when a single dispatch's requested child count is within budget.

    Returns False when ``requested`` exceeds ``max_fanout``.
    """
    if max_fanout is None:
        max_fanout = _tunable_int(_STATE_MAX_FANOUT, DEFAULT_MAX_FANOUT)
    try:
        return int(requested) <= int(max_fanout)
    except Exception:
        return False


# --- durable concurrency counter -------------------------------------------
def _load_entries() -> list[float]:
    try:
        raw = _db.get_runtime_state_value(_STATE_ACTIVE, [])
    except Exception:
        return []
    if not isinstance(raw, list):
        return []
    out: list[float] = []
    for item in raw:
        try:
            out.append(float(item))
        except Exception:
            continue
    return out


def _save_entries(entries: list[float]) -> None:
    try:
        _db.set_runtime_state_value(_STATE_ACTIVE, [float(e) for e in entries])
    except Exception:
        pass


def _fresh_entries(entries: list[float], now_ts: float, ttl: float) -> list[float]:
    """Drop entries older than ``ttl`` — reclaims slots left by crashed runs."""
    return [e for e in entries if (now_ts - e) <= ttl]


def try_enter(now_ts: float | None = None) -> bool:
    """Claim a concurrency slot.

    Increments the durable active counter and returns True only if the live
    (non-stale) count is below ``max_concurrent``. Stale entries older than the
    TTL are reclaimed first so a crashed dispatch never leaks a slot.
    """
    if now_ts is None:
        now_ts = time.time()
    ttl = _tunable_float(_STATE_TTL, DEFAULT_STALE_TTL_S)
    max_concurrent = _tunable_int(_STATE_MAX_CONCURRENT, DEFAULT_MAX_CONCURRENT)

    entries = _fresh_entries(_load_entries(), now_ts, ttl)
    if len(entries) >= max_concurrent:
        # Persist the reclaimed (shrunken) list even on refusal, so a future
        # caller sees the freed slots without needing another reclaim pass.
        _save_entries(entries)
        return False
    entries.append(float(now_ts))
    _save_entries(entries)
    return True


def exit(now_ts: float | None = None) -> None:
    """Release one concurrency slot (also reclaims stale entries)."""
    if now_ts is None:
        now_ts = time.time()
    ttl = _tunable_float(_STATE_TTL, DEFAULT_STALE_TTL_S)
    entries = _fresh_entries(_load_entries(), now_ts, ttl)
    if entries:
        # Remove the oldest live entry.
        entries.remove(min(entries))
    _save_entries(entries)


def effective_max_fanout() -> int:
    """The live fan-out ceiling (runtime-state override or default). Callers use it
    to cap+log a truncated fan-out rather than silently dropping children."""
    return _tunable_int(_STATE_MAX_FANOUT, DEFAULT_MAX_FANOUT)


def active_count(now_ts: float | None = None) -> int:
    """Number of live (non-stale) concurrency slots currently held."""
    if now_ts is None:
        now_ts = time.time()
    ttl = _tunable_float(_STATE_TTL, DEFAULT_STALE_TTL_S)
    return len(_fresh_entries(_load_entries(), now_ts, ttl))
