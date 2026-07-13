from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.services import recursion_guard as rg


# --- depth ------------------------------------------------------------------
def test_can_spawn_at_root(isolated_runtime):
    assert rg.can_spawn(0) is True


def test_can_spawn_blocked_at_max_depth(isolated_runtime):
    # default max_depth == 2
    assert rg.can_spawn(2) is False


def test_can_spawn_one_below_max(isolated_runtime):
    assert rg.can_spawn(1) is True


# --- fan-out ----------------------------------------------------------------
def test_fanout_allowed_at_limit(isolated_runtime):
    # default max_fanout == 8
    assert rg.fanout_allowed(8) is True


def test_fanout_blocked_over_limit(isolated_runtime):
    assert rg.fanout_allowed(9) is False


# --- concurrency counter ----------------------------------------------------
def test_try_enter_up_to_max_then_refuses(isolated_runtime):
    # default max_concurrent == 6
    for _ in range(6):
        assert rg.try_enter(now_ts=1000.0) is True
    assert rg.active_count(now_ts=1000.0) == 6
    # 7th is refused
    assert rg.try_enter(now_ts=1000.0) is False
    assert rg.active_count(now_ts=1000.0) == 6


def test_exit_frees_a_slot(isolated_runtime):
    for _ in range(6):
        assert rg.try_enter(now_ts=1000.0) is True
    assert rg.try_enter(now_ts=1000.0) is False
    rg.exit(now_ts=1000.0)
    assert rg.active_count(now_ts=1000.0) == 5
    # a slot is available again
    assert rg.try_enter(now_ts=1000.0) is True


def test_stale_entries_reclaimed_after_ttl(isolated_runtime):
    # Fill all 6 slots at t=1000.
    for _ in range(6):
        assert rg.try_enter(now_ts=1000.0) is True
    assert rg.try_enter(now_ts=1000.0) is False
    # default stale TTL == 600s. Past that, the crashed slots are reclaimed.
    later = 1000.0 + 601.0
    assert rg.active_count(now_ts=later) == 0
    assert rg.try_enter(now_ts=later) is True
    assert rg.active_count(now_ts=later) == 1


def test_thresholds_tunable_via_runtime_state(isolated_runtime):
    from core.runtime import db

    db.set_runtime_state_value("recursion_guard_max_depth", 3)
    db.set_runtime_state_value("recursion_guard_max_fanout", 2)
    db.set_runtime_state_value("recursion_guard_max_concurrent", 1)

    assert rg.can_spawn(2) is True  # now allowed (max_depth 3)
    assert rg.can_spawn(3) is False
    assert rg.fanout_allowed(2) is True
    assert rg.fanout_allowed(3) is False
    assert rg.try_enter(now_ts=500.0) is True
    assert rg.try_enter(now_ts=500.0) is False  # max_concurrent 1
