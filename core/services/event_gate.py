"""Shared non-LLM event-gate for generative daemons (Fase 2 Lag 5/7).

Generative daemons (``thought_stream``, ``reflection``, ``dreams`` …) fire an
LLM on a blind timer. This module is the cheap, non-LLM gate they call to fire
ONLY when a relevant signal actually moved — keeping the LLM's judgment, but
skipping the call when nothing meaningfully changed since the last fire.

Design
------
* **Durable baselines** — per-daemon, per-signal last-fired values live in
  :mod:`core.services.signal_baseline` (namespaced key ``f"{daemon}:{signal}"``),
  which round-trips across a process restart. No module-global store.
* **Fail-OPEN** — every path swallows errors toward *firing* (``True``), never
  toward silence. A broken gate degrades to the current timer behavior; it must
  never cost Jarvis his inner life.
* **Cold-start** — the very first time a daemon is seen (no baseline for ANY of
  its signals), the gate fires once and seeds the baselines.

Interface (other daemons code against this exact surface):
    event_driven_enabled() -> bool
    should_generative_fire(daemon_name, signals, *, min_delta=0.15, now=None) -> bool
"""

from __future__ import annotations

_FLAG_KEY = "event_driven_daemons"
_MIN_DELTA_KEY = "event_gate_min_delta"
_DEFAULT_MIN_DELTA = 0.15


def event_driven_enabled() -> bool:
    """True when the event-driven-daemons mode is switched on in runtime-state.

    Default False. Self-safe → False on any error (fall back to timer mode).
    """
    try:
        from core.runtime.db_core import get_runtime_state_value

        return bool(get_runtime_state_value(_FLAG_KEY, False))
    except Exception:
        return False


def _resolve_min_delta(default: float) -> float:
    """Runtime-tunable threshold. Falls back to ``default`` when unset/broken."""
    try:
        from core.runtime.db_core import get_runtime_state_value

        raw = get_runtime_state_value(_MIN_DELTA_KEY, default)
        return float(raw)
    except Exception:
        try:
            return float(default)
        except (TypeError, ValueError):
            return _DEFAULT_MIN_DELTA


def should_generative_fire(
    daemon_name: str,
    signals: dict[str, float],
    *,
    min_delta: float = _DEFAULT_MIN_DELTA,
    now: float | None = None,
) -> bool:
    """Decide whether ``daemon_name``'s LLM should fire this tick.

    * **Cold-start** (no stored baseline for ANY of the daemon's signals) →
      ``True``; seed all baselines.
    * Otherwise → ``True`` if ANY signal moved ``>= min_delta`` from its stored
      baseline; advance the baselines of the moved signals (record the fire).
      A signal with no baseline yet counts as moved.
    * All signals within ``min_delta`` → ``False`` (skip).
    * **Fail-OPEN** — any error → ``True``.
    """
    try:
        from core.services import signal_baseline

        name = str(daemon_name or "").strip()
        if not name or not signals:
            # Nothing to gate on — never silence: fire.
            return True

        delta = _resolve_min_delta(min_delta)
        keys = {sig: f"{name}:{sig}" for sig in signals}
        baselines = {sig: signal_baseline.get_baseline(keys[sig]) for sig in signals}

        # Cold-start: no baseline for ANY signal → fire once, seed everything.
        if all(base is None for base in baselines.values()):
            for sig, val in signals.items():
                signal_baseline.set_baseline(keys[sig], float(val))
            return True

        fired = False
        for sig, val in signals.items():
            value = float(val)
            base = baselines[sig]
            if base is None or abs(value - float(base)) >= delta:
                # Moved (or newly-appearing signal) → record the fire.
                signal_baseline.set_baseline(keys[sig], value)
                fired = True
        return fired
    except Exception:
        # A broken gate must FIRE, never silence Jarvis.
        return True
