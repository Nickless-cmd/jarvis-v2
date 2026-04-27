"""Provider circuit breaker — skip primaries that have been failing recently.

When a provider/model has failed N+ times in the last window, we stop
trying it for a cooldown period. This prevents the per-role fallback
chain from wasting 5+ seconds per call on a known-dead endpoint
(observed live with ollamafreeapi.com being down for hours).

Stateless on disk — kept in memory only. Acceptable because:
- Restarts are rare (maybe daily)
- A restart's fresh trial is actually useful (the provider may have come back)
- Persisting failure counts across restarts could permanently brick a
  recovered provider until manual intervention

API:
- record_failure(provider, model) — note a failure
- record_success(provider, model) — clear failure history
- should_skip(provider, model) — True if breaker is open
- breaker_state() — observability (for prompt awareness, debug tools)
"""
from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any

# Tunables
_FAILURE_THRESHOLD = 3            # N failures within window -> open the breaker
_FAILURE_WINDOW_SECONDS = 300.0   # 5 minutes of failure history kept
_OPEN_DURATION_SECONDS = 600.0    # 10 minutes skip when breaker opens

_LOCK = threading.Lock()
# (provider, model) -> deque[timestamp]
_FAILURES: dict[tuple[str, str], deque[float]] = {}
# (provider, model) -> timestamp when breaker was opened
_OPENED_AT: dict[tuple[str, str], float] = {}


def _key(provider: str, model: str) -> tuple[str, str]:
    return (str(provider or "").strip(), str(model or "").strip())


def _prune_old_failures(failures: deque[float], now: float) -> None:
    cutoff = now - _FAILURE_WINDOW_SECONDS
    while failures and failures[0] < cutoff:
        failures.popleft()


def record_failure(provider: str, model: str) -> dict[str, Any]:
    """Record a primary-call failure. Returns updated state for this key."""
    k = _key(provider, model)
    if not k[0] or not k[1]:
        return {"opened": False, "failure_count": 0}
    now = time.time()
    with _LOCK:
        failures = _FAILURES.setdefault(k, deque(maxlen=20))
        failures.append(now)
        _prune_old_failures(failures, now)
        if len(failures) >= _FAILURE_THRESHOLD and k not in _OPENED_AT:
            _OPENED_AT[k] = now
            opened = True
        else:
            opened = bool(k in _OPENED_AT)
    return {"opened": opened, "failure_count": len(failures)}


def record_success(provider: str, model: str) -> None:
    """Clear failure tracking on success — provider seems healthy again."""
    k = _key(provider, model)
    if not k[0] or not k[1]:
        return
    with _LOCK:
        _FAILURES.pop(k, None)
        _OPENED_AT.pop(k, None)


def should_skip(provider: str, model: str) -> bool:
    """True when breaker is open for this (provider, model)."""
    k = _key(provider, model)
    if not k[0] or not k[1]:
        return False
    now = time.time()
    with _LOCK:
        opened_at = _OPENED_AT.get(k)
        if opened_at is None:
            return False
        if now - opened_at >= _OPEN_DURATION_SECONDS:
            # Cooldown expired — half-open: allow next call to retry.
            _OPENED_AT.pop(k, None)
            _FAILURES.pop(k, None)
            return False
        return True


def breaker_state() -> dict[str, Any]:
    """Observability snapshot — returns open breakers + recent failure counts."""
    now = time.time()
    open_breakers: list[dict[str, Any]] = []
    recent_failures: list[dict[str, Any]] = []
    with _LOCK:
        for (prov, mod), opened_at in _OPENED_AT.items():
            seconds_open = max(0, int(now - opened_at))
            seconds_until_retry = max(0, int(_OPEN_DURATION_SECONDS - (now - opened_at)))
            open_breakers.append({
                "provider": prov,
                "model": mod,
                "opened_seconds_ago": seconds_open,
                "retry_in_seconds": seconds_until_retry,
            })
        for (prov, mod), failures in _FAILURES.items():
            count = len(failures)
            if count > 0:
                recent_failures.append({
                    "provider": prov,
                    "model": mod,
                    "failure_count": count,
                    "window_seconds": int(_FAILURE_WINDOW_SECONDS),
                })
    return {
        "open_breakers": open_breakers,
        "recent_failures": recent_failures,
        "threshold": _FAILURE_THRESHOLD,
        "window_seconds": int(_FAILURE_WINDOW_SECONDS),
        "open_duration_seconds": int(_OPEN_DURATION_SECONDS),
    }


def reset_all() -> None:
    """Test/admin helper — clear all state."""
    with _LOCK:
        _FAILURES.clear()
        _OPENED_AT.clear()
