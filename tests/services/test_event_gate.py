"""Tests for core.services.event_gate (Fase 2 Lag 5/7).

Shared non-LLM gate for generative daemons. Daemons call this cheap gate to
decide whether their (expensive) LLM should fire at all: fire only when a
relevant signal actually moved, otherwise skip. The gate is FAIL-OPEN — a
broken gate must fall back to FIRING, never silence Jarvis' inner life.

Baselines are durable via core.services.signal_baseline (namespaced per
daemon: ``f"{daemon_name}:{signal}"``).
"""

import importlib


def _fresh_module():
    import core.services.event_gate as eg

    importlib.reload(eg)
    return eg


def _clear_baselines():
    import core.services.signal_baseline as sb

    importlib.reload(sb)
    sb.clear_all()
    return sb


# ---------------------------------------------------------------- flag


def test_event_driven_enabled_false_by_default(isolated_runtime):
    eg = _fresh_module()
    assert eg.event_driven_enabled() is False


def test_event_driven_enabled_true_when_flag_set(isolated_runtime, monkeypatch):
    eg = _fresh_module()

    from core.runtime import db_core

    def _fake(key, default=None):
        if key == "event_driven_daemons":
            return True
        return default

    monkeypatch.setattr(db_core, "get_runtime_state_value", _fake)
    assert eg.event_driven_enabled() is True


def test_event_driven_enabled_false_on_error(isolated_runtime, monkeypatch):
    eg = _fresh_module()

    from core.runtime import db_core

    def _boom(key, default=None):
        raise RuntimeError("kv down")

    monkeypatch.setattr(db_core, "get_runtime_state_value", _boom)
    assert eg.event_driven_enabled() is False


# ---------------------------------------------------------------- gate


def test_cold_start_fires_and_sets_baselines(isolated_runtime):
    sb = _clear_baselines()
    eg = _fresh_module()

    # No baseline for ANY of the daemon's signals -> fire once to seed.
    assert eg.should_generative_fire("thought_stream", {"mood": 0.5, "novelty": 0.2}) is True

    # Baselines were established (namespaced per daemon).
    assert sb.get_baseline("thought_stream:mood") == 0.5
    assert sb.get_baseline("thought_stream:novelty") == 0.2


def test_flat_signals_skip(isolated_runtime):
    _clear_baselines()
    eg = _fresh_module()

    # Seed baselines.
    eg.should_generative_fire("reflection", {"mood": 0.50, "novelty": 0.20})

    # Nothing moved past min_delta -> skip.
    assert (
        eg.should_generative_fire("reflection", {"mood": 0.55, "novelty": 0.18}) is False
    )


def test_moving_signal_fires_and_advances_baseline(isolated_runtime):
    sb = _clear_baselines()
    eg = _fresh_module()

    eg.should_generative_fire("reflection", {"mood": 0.50, "novelty": 0.20})

    # mood jumps 0.50 -> 0.80 (delta 0.30 >= 0.15) -> fire.
    assert (
        eg.should_generative_fire("reflection", {"mood": 0.80, "novelty": 0.20}) is True
    )
    # The moved baseline advanced (records the fire); the flat one is untouched.
    assert sb.get_baseline("reflection:mood") == 0.80
    assert sb.get_baseline("reflection:novelty") == 0.20

    # Immediately again with the same values -> now flat -> skip.
    assert (
        eg.should_generative_fire("reflection", {"mood": 0.80, "novelty": 0.20})
        is False
    )


def test_min_delta_tunable_via_runtime_state(isolated_runtime, monkeypatch):
    _clear_baselines()
    eg = _fresh_module()

    eg.should_generative_fire("dreams", {"drift": 0.50})

    from core.runtime import db_core

    real = db_core.get_runtime_state_value

    def _tuned(key, default=None):
        if key == "event_gate_min_delta":
            return 0.05  # tighter threshold
        return real(key, default)

    monkeypatch.setattr(db_core, "get_runtime_state_value", _tuned)

    # 0.08 move would be BELOW the 0.15 default but ABOVE the tuned 0.05.
    assert eg.should_generative_fire("dreams", {"drift": 0.58}) is True


def test_fail_open_on_internal_error(isolated_runtime, monkeypatch):
    _clear_baselines()
    eg = _fresh_module()

    import core.services.signal_baseline as sb

    def _boom(*a, **k):
        raise RuntimeError("baseline store exploded")

    monkeypatch.setattr(sb, "get_baseline", _boom)

    # A broken gate must FIRE, never silence Jarvis.
    assert eg.should_generative_fire("thought_stream", {"mood": 0.5}) is True


def test_durable_baselines_across_simulated_restart(isolated_runtime):
    _clear_baselines()
    eg = _fresh_module()
    eg.should_generative_fire("reflection", {"mood": 0.50})

    from core.runtime import db_core

    db_core.clear_runtime_state_cache()
    eg2 = _fresh_module()  # fresh import = simulated restart

    # Baseline survived: a flat re-read skips instead of cold-start firing.
    assert eg2.should_generative_fire("reflection", {"mood": 0.52}) is False
