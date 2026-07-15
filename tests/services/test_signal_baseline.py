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


# --------------------------------------------------------------------------- #
# Bilag 2 — scope namespacing ("one self, many projections")
# --------------------------------------------------------------------------- #
def test_default_path_unchanged_by_scope_feature(isolated_runtime):
    """(1) The global (scope=None) path behaves EXACTLY as before."""
    sb = _fresh_module()
    sb.clear_all()
    sb.set_baseline("cpu.load", 0.42)
    assert sb.get_baseline("cpu.load") == 0.42
    # global cold-start still counts only the global store
    assert sb.is_cold_start(min_signals=1) is False
    assert sb.is_cold_start(min_signals=2) is True


def test_two_scopes_are_independent(isolated_runtime):
    """(2) Two different scopes get fully independent baselines."""
    sb = _fresh_module()
    sb.clear_all()
    sb.clear_all(scope="userA")
    sb.clear_all(scope="userB")

    sb.set_baseline("frustration", 0.20, scope="userA")
    sb.set_baseline("frustration", 0.90, scope="userB")

    assert sb.get_baseline("frustration", scope="userA") == 0.20
    assert sb.get_baseline("frustration", scope="userB") == 0.90
    # and neither touched the global namespace
    assert sb.get_baseline("frustration") is None


def test_scoped_write_does_not_leak_into_global_or_other_scope(isolated_runtime):
    """(3) A user-scoped baseline never leaks into another user's scope."""
    sb = _fresh_module()
    sb.clear_all()
    sb.clear_all(scope="userA")
    sb.clear_all(scope="userB")

    sb.set_baseline("tension", 0.77, scope="userA")

    assert sb.get_baseline("tension", scope="userB") is None
    assert sb.get_baseline("tension") is None
    # userB's namespace stays cold; userA's does not
    assert sb.is_cold_start(min_signals=1, scope="userB") is True
    assert sb.is_cold_start(min_signals=1, scope="userA") is False


def test_scoped_cold_start_does_not_inflate_global(isolated_runtime):
    """Per-scope cold-start counts are disjoint from the global count."""
    sb = _fresh_module()
    sb.clear_all()
    sb.clear_all(scope="userA")

    # fill a scope with 3 signals
    sb.set_baseline("a", 1.0, scope="userA")
    sb.set_baseline("b", 2.0, scope="userA")
    sb.set_baseline("c", 3.0, scope="userA")
    assert sb.is_cold_start(min_signals=3, scope="userA") is False
    # global namespace is untouched → still cold
    assert sb.is_cold_start(min_signals=3) is True


def test_scoped_durable_across_simulated_restart(isolated_runtime):
    sb = _fresh_module()
    sb.clear_all(scope="userA")
    sb.set_baseline("mood", 0.33, scope="userA")

    from core.runtime import db_core

    db_core.clear_runtime_state_cache()
    sb2 = _fresh_module()  # simulated restart

    assert sb2.get_baseline("mood", scope="userA") == 0.33
    assert sb2.get_baseline("mood", scope="userB") is None
