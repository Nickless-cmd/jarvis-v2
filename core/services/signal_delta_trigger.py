"""Signal-delta trigger (C2) — pure, NON-LLM event-driven dispatch decision.

Replaces a blind 30-min timer. A daemon today fires an (expensive) LLM every
30 minutes regardless of whether anything changed. This module is the cheap
pure function evaluated each heartbeat that decides whether a *real* change in
Jarvis' signals warrants a dispatch — and, critically, refuses to fire on
noise or flapping so it never out-burns the timer it replaces.

Guarantees:
  * **Pure / NON-LLM.** ``evaluate`` never calls any LLM/provider. It only
    reads baselines (C1) and durable runtime-state.
  * **Self-safe.** Any error → ``None`` (fail-closed: never fire on error).
  * **Composite-coalesced.** At most ONE decision per call, carrying ALL
    crossed signals — never one decision per signal.

Guards (each is an economic guard against burning more than the timer):
  * **Cold-start suppression** — on first sight, establish baselines, never fire.
  * **Hysteresis (Schmitt).** A signal fires when ``|value - baseline| >=
    θ_high``. On firing its baseline advances to the new value and it becomes
    "hot"; while hot it is suppressed until it *settles* back within θ_low of
    baseline (θ_low < θ_high). Kills flapping around the threshold. The hot
    set is DURABLE (runtime-state) so hysteresis survives restart.
  * **Debounce / cooldown.** After any dispatch, a global cooldown (default
    1200s) suppresses further dispatch. The cooldown timestamp is DURABLE
    (runtime-state) so it survives restart.
  * **Absolute-floor OR.** A signal also crosses if its absolute value >=
    θ_abs even with a tiny delta — catches slow-boil drift that never trips
    the delta.

All thresholds are tunable at runtime (runtime-state) without a deploy.
"""
from __future__ import annotations

import time as _time
from typing import Optional

# Durable runtime-state keys.
_KEY_PREFIX = "signal_delta_trigger:"
_KEY_LAST_DISPATCH = _KEY_PREFIX + "last_dispatch_ts"
_KEY_HOT = _KEY_PREFIX + "hot_signals"

# Tunable defaults (override via runtime-state key ``signal_delta_trigger:<name>``).
_DEFAULT_THETA_HIGH = 0.30
_DEFAULT_THETA_LOW = 0.15
_DEFAULT_THETA_ABS = 0.85
_DEFAULT_COOLDOWN_S = 1200.0


def _db():
    """Lazy import so this module is importable/pure without a live DB, and so
    tests (and isolated_runtime reloads) always get the current db_core."""
    from core.runtime import db_core

    return db_core


def _baseline():
    """Lazy import of C1's baseline module (built in parallel)."""
    from core.services import signal_baseline

    return signal_baseline


def _cfg_float(db, name: str, default: float) -> float:
    try:
        return float(db.get_runtime_state_value(_KEY_PREFIX + name, default))
    except Exception:
        return float(default)


def _load_float(db, key: str, default: float) -> float:
    try:
        return float(db.get_runtime_state_value(key, default))
    except Exception:
        return float(default)


def _store_float(db, key: str, value: float) -> None:
    try:
        db.set_runtime_state_value(key, float(value))
    except Exception:
        pass


def _load_hot(db) -> dict[str, bool]:
    try:
        raw = db.get_runtime_state_value(_KEY_HOT, None)
        if isinstance(raw, dict):
            return {str(k): bool(v) for k, v in raw.items()}
    except Exception:
        pass
    return {}


def _store_hot(db, hot: dict[str, bool]) -> None:
    try:
        db.set_runtime_state_value(_KEY_HOT, {str(k): bool(v) for k, v in hot.items()})
    except Exception:
        pass


def _reason(crossed: list[str], movements: dict[str, float], theta_abs: float) -> str:
    parts = []
    for name in crossed:
        delta = movements.get(name, 0.0)
        parts.append(f"{name} Δ{delta:+.3f}")
    return "signal-delta dispatch: " + ", ".join(parts)


def evaluate(signals: dict[str, float]) -> Optional[dict]:
    """Decide whether a real change warrants a dispatch.

    Returns ``None`` when nothing should dispatch. Otherwise returns ONE
    decision dict ``{"crossed": [...], "movements": {sig: delta}, "reason": str}``
    carrying every signal that crossed this call.
    """
    try:
        if not signals:
            return None

        # Coerce input; drop non-numeric entries defensively.
        clean: dict[str, float] = {}
        for k, v in signals.items():
            try:
                clean[str(k)] = float(v)
            except Exception:
                continue
        if not clean:
            return None

        baseline = _baseline()

        # --- Cold-start suppression: establish baselines, never fire. ---------
        try:
            cold = baseline.is_cold_start()
        except Exception:
            cold = False
        if cold:
            for name, val in clean.items():
                try:
                    baseline.set_baseline(name, val)
                except Exception:
                    pass
            return None

        db = _db()
        theta_high = _cfg_float(db, "theta_high", _DEFAULT_THETA_HIGH)
        theta_low = _cfg_float(db, "theta_low", _DEFAULT_THETA_LOW)
        theta_abs = _cfg_float(db, "theta_abs", _DEFAULT_THETA_ABS)
        cooldown_s = _cfg_float(db, "cooldown_s", _DEFAULT_COOLDOWN_S)
        # Invariant: θ_low < θ_high (else hysteresis degenerates).
        if theta_low >= theta_high:
            theta_low = theta_high / 2.0

        now = _time.time()
        last_ts = _load_float(db, _KEY_LAST_DISPATCH, 0.0)
        in_cooldown = (now - last_ts) < cooldown_s

        hot = _load_hot(db)

        crossed: list[str] = []
        movements: dict[str, float] = {}
        new_baselines: dict[str, float] = {}
        settle_changed = False  # hot->settled transitions persist independent of dispatch

        for name, val in clean.items():
            b = baseline.get_baseline(name)
            if b is None:
                # Newly seen signal (post cold-start): seed baseline, never fire.
                try:
                    baseline.set_baseline(name, val)
                except Exception:
                    pass
                continue

            absdelta = abs(val - b)

            if hot.get(name, False):
                # Suppressed while hot; can only re-arm once it settles back
                # within θ_low of baseline. This kills flapping around θ_high.
                if absdelta <= theta_low:
                    hot[name] = False
                    settle_changed = True
                continue

            # Cross on delta OR on absolute floor (slow-boil drift).
            # TODO: refine absolute-floor with a "held for T" dwell so a signal
            # that merely sits above θ_abs cannot re-trip after each settle.
            if absdelta >= theta_high or val >= theta_abs:
                crossed.append(name)
                movements[name] = val - b
                new_baselines[name] = val

        # --- Dispatch decision (composite-coalesced) --------------------------
        if crossed and not in_cooldown:
            crossed_sorted = sorted(crossed)
            for name in crossed_sorted:
                # Advance baseline to the new value and arm hysteresis.
                try:
                    baseline.set_baseline(name, new_baselines[name])
                except Exception:
                    pass
                hot[name] = True
            _store_hot(db, hot)
            _store_float(db, _KEY_LAST_DISPATCH, now)
            return {
                "crossed": crossed_sorted,
                "movements": {n: movements[n] for n in crossed_sorted},
                "reason": _reason(crossed_sorted, movements, theta_abs),
            }

        # No dispatch (nothing crossed, or crossed-but-in-cooldown). We do NOT
        # advance baselines or arm hot for the crossed-but-cooled signals — the
        # change stays "pending" and can fire once cooldown expires. Only the
        # settle transitions (hysteresis release) are durably persisted.
        if settle_changed:
            _store_hot(db, hot)
        return None
    except Exception:
        # Self-safe: any failure must NOT fire (fail-closed).
        return None
