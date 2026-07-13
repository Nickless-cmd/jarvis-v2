"""Persisted signal-baseline with cold-start guard (Task C1).

Durable memory for an event-driven trigger. It remembers each signal's last
recorded value across process restarts. Jarvis reboots often; an in-memory
store would forget every baseline at boot and let the delta-trigger fire on
the very first observation of each signal — a false-fire storm. Persisting to
the runtime-state KV (``runtime_state_kv``) avoids that.

Design decisions
----------------
* **Durable store** — a single namespaced KV key ``signal_baselines`` holding
  a JSON dict ``signal -> float``. Persisted via
  ``core.runtime.db_core.get/set_runtime_state_value`` (sqlite-backed), so it
  round-trips across a simulated restart. No module-global dict is used as the
  store.
* **Self-safe** — any read/write error fails toward *suppression*, never
  toward firing: ``get_baseline`` returns None, ``set_baseline`` is a no-op,
  ``is_cold_start`` returns True.

Interface (other modules code against this exact surface):
    get_baseline(signal) -> float | None
    set_baseline(signal, value) -> None
    is_cold_start(min_signals=3) -> bool
    clear_all() -> None   # test helper
"""

from __future__ import annotations

_STORE_KEY = "signal_baselines"


def _load() -> dict[str, float]:
    """Read the whole baseline dict from the durable store. Fail-closed to {}."""
    try:
        from core.runtime.db_core import get_runtime_state_value

        raw = get_runtime_state_value(_STORE_KEY, {})
        if not isinstance(raw, dict):
            return {}
        out: dict[str, float] = {}
        for key, val in raw.items():
            try:
                out[str(key)] = float(val)
            except (TypeError, ValueError):
                continue
        return out
    except Exception:
        return {}


def _save(baselines: dict[str, float]) -> bool:
    try:
        from core.runtime.db_core import set_runtime_state_value

        set_runtime_state_value(_STORE_KEY, baselines)
        return True
    except Exception:
        return False


def get_baseline(signal: str) -> float | None:
    """Last recorded value for ``signal``; None if never recorded."""
    name = str(signal or "").strip()
    if not name:
        return None
    try:
        return _load().get(name)
    except Exception:
        return None


def set_baseline(signal: str, value: float) -> None:
    """Persist ``value`` durably as the new baseline for ``signal``.

    Self-safe: an unparseable value or a store error is a silent no-op.
    """
    name = str(signal or "").strip()
    if not name:
        return
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return
    try:
        baselines = _load()
        baselines[name] = numeric
        _save(baselines)
    except Exception:
        return


def is_cold_start(min_signals: int = 3) -> bool:
    """True until at least ``min_signals`` distinct baselines have been recorded.

    Used to suppress delta-firing right after boot until a fresh baseline
    exists. Fails toward suppression (True) on any error.
    """
    try:
        threshold = int(min_signals)
    except (TypeError, ValueError):
        return True
    if threshold <= 0:
        return False
    try:
        return len(_load()) < threshold
    except Exception:
        return True


def clear_all() -> None:
    """Drop all baselines (test helper). Self-safe."""
    try:
        _save({})
    except Exception:
        return
