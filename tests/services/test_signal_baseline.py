"""Tests for core.services.signal_baseline (Task C1).

Persisted signal-baseline with cold-start guard. The durable store is the
runtime-state KV (runtime_state_kv), so baselines survive a process restart
and do not cause a false-fire storm at boot.
"""

import importlib


def _fresh_module():
    import core.services.signal_baseline as sb

    importlib.reload(sb)
    return sb


def test_get_returns_none_on_cold_start(isolated_runtime):
    sb = _fresh_module()
    sb.clear_all()
    assert sb.get_baseline("cpu.load") is None


def test_set_get_round_trip(isolated_runtime):
    sb = _fresh_module()
    sb.clear_all()
    sb.set_baseline("cpu.load", 0.42)
    assert sb.get_baseline("cpu.load") == 0.42


def test_is_cold_start_until_min_signals(isolated_runtime):
    sb = _fresh_module()
    sb.clear_all()
    assert sb.is_cold_start(min_signals=3) is True
    sb.set_baseline("a", 1.0)
    sb.set_baseline("b", 2.0)
    assert sb.is_cold_start(min_signals=3) is True
    sb.set_baseline("c", 3.0)
    assert sb.is_cold_start(min_signals=3) is False
    # distinct-signal count, not write count: re-writing an existing signal
    # does not push a 2-signal store past the threshold.
    sb.clear_all()
    sb.set_baseline("a", 1.0)
    sb.set_baseline("a", 9.0)
    sb.set_baseline("b", 2.0)
    assert sb.is_cold_start(min_signals=3) is True


def test_durable_across_simulated_restart(isolated_runtime):
    """Write via one call path, then read via a simulated restart.

    A restart = every in-memory cache is gone and the value is re-read from
    the durable store (runtime_state_kv in sqlite). We clear both the
    db_core runtime-state cache and reload the module (dropping any module
    cache) to prove the value came from disk, not memory.
    """
    sb = _fresh_module()
    sb.clear_all()
    sb.set_baseline("disk.temp", 55.5)

    from core.runtime import db_core

    db_core.clear_runtime_state_cache()
    sb2 = _fresh_module()  # fresh import = simulated restart

    assert sb2.get_baseline("disk.temp") == 55.5
    assert sb2.is_cold_start(min_signals=1) is False


def test_clear_all(isolated_runtime):
    sb = _fresh_module()
    sb.set_baseline("x", 1.0)
    sb.clear_all()
    assert sb.get_baseline("x") is None
    assert sb.is_cold_start() is True
