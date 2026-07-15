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
    get_baseline(signal, scope=None) -> float | None
    set_baseline(signal, value, scope=None) -> None
    is_cold_start(min_signals=3, scope=None) -> bool
    clear_all(scope=None) -> None   # test helper

Scoping ("one self, many projections", Bilag 2)
-----------------------------------------------
An OPTIONAL ``scope`` namespaces the durable KV *partition*:

* ``scope=None`` — the GLOBAL self-signals (somatic, mood, identity, …). This
  is the original behaviour, byte-for-byte: it stores under ``signal_baselines``
  and its cold-start count is exactly ``len`` of that dict. Every default call
  path is unchanged.
* ``scope="<user_id>"`` (or ``"<user_id>:<session>"``) — a per-relation
  namespace for USER/SESSION signals (frustration-with-this-user, conversation
  context). Stored under a SEPARATE KV key ``signal_baselines:<scope>`` so that
  two scopes get fully independent baselines and one relation's delta can never
  leak into another's — and so a scope's cold-start count never inflates the
  global one. Same store (runtime_state_kv), disjoint key-spaces.
"""

from __future__ import annotations

_STORE_KEY = "signal_baselines"


def _store_key(scope: str | None) -> str:
    """Durable KV key for ``scope``. None/empty → the global key, unchanged."""
    name = str(scope or "").strip()
    if not name:
        return _STORE_KEY
    return f"{_STORE_KEY}:{name}"


def _load(scope: str | None = None) -> dict[str, float]:
    """Read the whole baseline dict for ``scope``. Fail-closed to {}."""
    try:
        from core.runtime.db_core import get_runtime_state_value

        raw = get_runtime_state_value(_store_key(scope), {})
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


def _save(baselines: dict[str, float], scope: str | None = None) -> bool:
    try:
        from core.runtime.db_core import set_runtime_state_value

        set_runtime_state_value(_store_key(scope), baselines)
        return True
    except Exception:
        return False


def get_baseline(signal: str, scope: str | None = None) -> float | None:
    """Last recorded value for ``signal`` in ``scope``; None if never recorded."""
    name = str(signal or "").strip()
    if not name:
        return None
    try:
        return _load(scope).get(name)
    except Exception:
        return None


def set_baseline(signal: str, value: float, scope: str | None = None) -> None:
    """Persist ``value`` durably as the new baseline for ``signal`` in ``scope``.

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
        baselines = _load(scope)
        baselines[name] = numeric
        _save(baselines, scope)
    except Exception:
        return


def is_cold_start(min_signals: int = 3, scope: str | None = None) -> bool:
    """True until ``min_signals`` distinct baselines exist *within* ``scope``.

    Used to suppress delta-firing right after boot until a fresh baseline
    exists. Per-scope: a fresh user relation is cold-started independently of
    the global self-signals. Fails toward suppression (True) on any error.
    """
    try:
        threshold = int(min_signals)
    except (TypeError, ValueError):
        return True
    if threshold <= 0:
        return False
    try:
        return len(_load(scope)) < threshold
    except Exception:
        return True


def clear_all(scope: str | None = None) -> None:
    """Drop all baselines in ``scope`` (test helper). Self-safe."""
    try:
        _save({}, scope)
    except Exception:
        return
