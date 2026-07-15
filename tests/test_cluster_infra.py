"""E2E tests for the infra/maintenance cluster-daemon family #10 (the LAST family).

Consolidation contract:
* the family folds cache_maintenance + signal_decay + cost_optimization +
  ground_truth_registry + wakeup_cleanup + file_awareness + mail_checker +
  visual_memory into ONE Central-governed family;
* this family has NO LLM member — every member is rules/DB-driven (visual_memory
  uses a LOCAL vision model at 0 API tokens) and runs in the UNCONDITIONAL tier and
  self-throttles on its own cadence; the family's one gate is fail-open (no gated
  signals → always fires);
* cache_maintenance + signal_decay self-throttle INTERNALLY (family calls every
  tick); file_awareness runs every tick (idempotent watcher-ensure); wakeup_cleanup
  / cost_optimization / ground_truth_registry (60min), mail_checker (15min) and
  visual_memory (360min) self-throttle on the cadence the family gives them;
* a member error never crashes the family — one failing maintenance daemon never
  blocks the others; the tick never raises;
* the 8 old daemons are RETIRED and cluster_infra is registered LIVE.

Patches target the NEW module cluster_daemon_families (not cluster_daemon).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import core.services.cluster_daemon_families as cdmf

# member name -> (module, tick/run fn) each unconditional member dispatches to.
_MEMBER_TICKS = {
    "file_awareness": ("core.services.file_awareness_daemon", "tick_file_awareness"),
    "cache_maintenance": ("core.services.cache_maintenance_daemon", "tick_cache_maintenance_daemon"),
    "signal_decay": ("core.services.signal_decay_daemon", "tick_signal_decay_daemon"),
    "wakeup_cleanup": ("core.services.self_wakeup", "tick_wakeup_cleanup"),
    "cost_optimization": ("core.services.cost_optimization_daemon", "tick"),
    "ground_truth_registry": ("core.services.ground_truth_registry", "ground_truth_daemon_tick"),
    "mail_checker": ("core.services.mail_checker_daemon", "tick_mail_checker_daemon"),
    "visual_memory": ("core.services.visual_memory", "tick_visual_memory_daemon"),
}

# Members that run EVERY tick (no family throttle): internal-throttle maintenance +
# the idempotent file_awareness watcher-ensure.
_EVERY_TICK = {"file_awareness", "cache_maintenance", "signal_decay"}
# Members the family self-throttles (had no internal timer) → cadence in minutes.
_FAMILY_THROTTLED = {
    "wakeup_cleanup": 60,
    "cost_optimization": 60,
    "ground_truth_registry": 60,
    "mail_checker": 15,
    "visual_memory": 360,
}


def _reset_throttle() -> None:
    """Clear the family's per-member self-throttle so members are ready to run."""
    cdmf._INFRA_THROTTLE.clear()


def _patch_member_ticks(stack: ExitStack) -> dict[str, MagicMock]:
    mocks: dict[str, MagicMock] = {}
    for member, (mod, fn) in _MEMBER_TICKS.items():
        m = MagicMock(return_value={"status": "ok", "member": member})
        stack.enter_context(patch(f"{mod}.{fn}", m))
        mocks[member] = m
    return mocks


def _patch_env(stack: ExitStack, *, gate_fires: bool = True) -> None:
    stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
    stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=gate_fires))
    stack.enter_context(patch("core.services.central_core.central"))


# ---------------------------------------------------------------------------
# Structure: no LLM/gated member; all 8 in the unconditional tier
# ---------------------------------------------------------------------------


def test_infra_family_has_no_gated_llm_member():
    fam = cdmf.build_infra_family()
    assert fam.family_name == "cluster_infra"
    assert fam.members == [], "infra family is all-rules — the gated tier is empty"


def test_all_eight_members_in_unconditional_tier():
    names = [name for name, _ in cdmf._INFRA_UNCONDITIONAL]
    assert names[0] == "file_awareness", "cheap load-bearing tamper-ensure runs FIRST"
    assert set(names) == {
        "file_awareness",
        "cache_maintenance",
        "signal_decay",
        "wakeup_cleanup",
        "cost_optimization",
        "ground_truth_registry",
        "mail_checker",
        "visual_memory",
    }
    assert len(names) == 8


# ---------------------------------------------------------------------------
# All 8 run in a single family tick, each old tick fn invoked (outputs preserved)
# ---------------------------------------------------------------------------


def test_all_members_run_in_one_tick():
    _reset_throttle()
    with ExitStack() as stack:
        mocks = _patch_member_ticks(stack)
        _patch_env(stack)
        result = cdmf.tick_cluster_infra()

    assert set(result["members_ran"]) == set(_MEMBER_TICKS.keys())
    for member, m in mocks.items():
        assert m.call_count == 1, f"{member} old tick fn must be invoked (output preserved)"


def test_gate_off_does_not_block_unconditional_members():
    """The (fail-open) family gate must never be able to block the maintenance tier."""
    _reset_throttle()
    with ExitStack() as stack:
        mocks = _patch_member_ticks(stack)
        _patch_env(stack, gate_fires=False)
        result = cdmf.tick_cluster_infra()

    assert set(result["members_ran"]) == set(_MEMBER_TICKS.keys())
    for m in mocks.values():
        assert m.call_count == 1


def test_members_run_even_if_gated_family_tick_raises():
    """Even a catastrophic family-gate tick failure cannot skip the maintenance tier."""
    _reset_throttle()
    broken = MagicMock(side_effect=RuntimeError("gate boom"))
    fake_family = MagicMock()
    fake_family.tick = broken
    with ExitStack() as stack:
        mocks = _patch_member_ticks(stack)
        stack.enter_context(patch("core.services.central_core.central"))
        stack.enter_context(patch.object(cdmf, "infra_family", return_value=fake_family))
        result = cdmf.tick_cluster_infra()

    for m in mocks.values():
        assert m.call_count == 1
    assert "__gated__" in result["member_errors"]
    assert "boom" in result["member_errors"]["__gated__"]


# ---------------------------------------------------------------------------
# Every-tick members (internal-throttle maintenance + file_awareness ensure)
# ---------------------------------------------------------------------------


def test_every_tick_members_run_on_each_of_n_ticks():
    """cache_maintenance/signal_decay self-throttle INTERNALLY and file_awareness is
    idempotent, so the family calls them on every one of N consecutive ticks."""
    _reset_throttle()
    with ExitStack() as stack:
        mocks = _patch_member_ticks(stack)
        _patch_env(stack)
        for _ in range(3):
            cdmf.tick_cluster_infra()

    for member in _EVERY_TICK:
        assert mocks[member].call_count == 3, f"{member} must run every tick"


# ---------------------------------------------------------------------------
# Family-throttled members self-throttle on their own cadence
# ---------------------------------------------------------------------------


def test_family_throttled_members_run_once_then_throttle():
    _reset_throttle()
    with ExitStack() as stack:
        mocks = _patch_member_ticks(stack)
        _patch_env(stack)
        cdmf.tick_cluster_infra()   # first tick: throttle ready → runs
        cdmf.tick_cluster_infra()   # immediate second tick: throttled

    for member in _FAMILY_THROTTLED:
        assert mocks[member].call_count == 1, f"{member} must self-throttle after first tick"
    # every-tick members drained on BOTH ticks
    for member in _EVERY_TICK:
        assert mocks[member].call_count == 2


def test_throttled_member_still_recorded_as_run():
    """A throttled member returns a self-throttle marker but still counts as run so
    the heartbeat sees it participated (parity with the other families)."""
    _reset_throttle()
    with ExitStack() as stack:
        _patch_member_ticks(stack)
        _patch_env(stack)
        cdmf.tick_cluster_infra()
        result = cdmf.tick_cluster_infra()  # second tick → throttled members

    for member, cadence in _FAMILY_THROTTLED.items():
        assert result["outputs"][member]["status"] == "throttled"
        assert result["outputs"][member]["cadence_minutes"] == cadence
        assert member in result["members_ran"]


def test_throttle_ready_helper_respects_cadence():
    _reset_throttle()
    assert cdmf._infra_throttle_ready("k", 60) is True   # first call always ready
    assert cdmf._infra_throttle_ready("k", 60) is False  # immediate re-call throttled
    # a different key is independent
    assert cdmf._infra_throttle_ready("other", 15) is True


# ---------------------------------------------------------------------------
# Error isolation — a failing maintenance daemon never blocks the others
# ---------------------------------------------------------------------------


def test_failing_member_never_blocks_siblings():
    _reset_throttle()
    with ExitStack() as stack:
        mocks = _patch_member_ticks(stack)
        mocks["mail_checker"].side_effect = RuntimeError("imap boom")
        _patch_env(stack)
        result = cdmf.tick_cluster_infra()

    # failing member is isolated ...
    assert "mail_checker" in result["member_errors"]
    assert "boom" in result["member_errors"]["mail_checker"]
    # ... but every other member still ran
    for member in _MEMBER_TICKS:
        if member == "mail_checker":
            continue
        assert member in result["members_ran"], f"{member} must run despite sibling error"
        assert mocks[member].call_count == 1


def test_first_member_error_isolated_and_family_survives():
    """Even the FIRST member failing must not block the rest of the tier."""
    _reset_throttle()
    with ExitStack() as stack:
        mocks = _patch_member_ticks(stack)
        mocks["file_awareness"].side_effect = RuntimeError("watcher boom")
        _patch_env(stack)
        result = cdmf.tick_cluster_infra()

    assert "file_awareness" in result["member_errors"]
    assert "cache_maintenance" in result["members_ran"]
    assert "visual_memory" in result["members_ran"]


# ---------------------------------------------------------------------------
# Self-safety — the entry point never raises into the heartbeat
# ---------------------------------------------------------------------------


def test_entrypoint_never_raises_on_broken_family():
    _reset_throttle()
    with ExitStack() as stack:
        mocks = _patch_member_ticks(stack)
        stack.enter_context(patch("core.services.central_core.central"))
        stack.enter_context(patch.object(cdmf, "infra_family", side_effect=RuntimeError("family down")))
        result = cdmf.tick_cluster_infra()

    assert result["family"] == "cluster_infra"
    assert "__gated__" in result["member_errors"]
    # even with the family object broken, the maintenance tier still ran
    for m in mocks.values():
        assert m.call_count == 1


def test_entrypoint_survives_broken_snapshot():
    _reset_throttle()
    with ExitStack() as stack:
        mocks = _patch_member_ticks(stack)
        _patch_env(stack)
        stack.enter_context(patch.object(cdmf, "_collect_infra_snapshot", side_effect=RuntimeError("snap boom")))
        result = cdmf.tick_cluster_infra()

    # snapshot failure degrades to a neutral snap; the members still run
    assert result["family"] == "cluster_infra"
    for m in mocks.values():
        assert m.call_count == 1


def test_entrypoint_runs_live_by_default():
    _reset_throttle()
    with ExitStack() as stack:
        _patch_member_ticks(stack)
        _patch_env(stack)
        result = cdmf.tick_cluster_infra()
    assert result["shadow"] is False


def test_snapshot_is_empty_and_safe():
    assert cdmf._collect_infra_snapshot() == {}


# ---------------------------------------------------------------------------
# Registration + retirement in daemon_manager
# ---------------------------------------------------------------------------


def test_cluster_infra_registered_live():
    from core.services import daemon_manager as dm

    assert "cluster_infra" in dm.get_daemon_names()
    states = {d["name"]: d for d in dm.get_all_daemon_states()}
    entry = states["cluster_infra"]
    assert entry["enabled"] is True
    assert "infra" in entry["description"]


def test_eight_old_daemons_retired():
    from core.services import daemon_manager as dm

    retired = [
        "cache_maintenance",
        "signal_decay",
        "cost_optimization",
        "ground_truth_registry",
        "wakeup_cleanup",
        "file_awareness",
        "mail_checker",
        "visual_memory",
    ]
    with patch.object(dm, "_load_state", return_value={}):
        for name in retired:
            assert dm._REGISTRY[name].get("default_enabled") is False, f"{name} must default disabled"
            assert dm._REGISTRY[name].get("retired") == "2026-07-15", f"{name} missing retired marker"
            assert "cluster_infra" in dm._REGISTRY[name]["description"], f"{name} desc must point to cluster_infra"
            assert dm.is_enabled(name) is False, f"{name} must be disabled (retired)"
