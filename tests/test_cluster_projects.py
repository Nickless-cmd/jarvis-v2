"""E2E tests for the projects cluster-daemon family #9.

Consolidation contract:
* the family folds task_worker + my_projects_watchdog + life_projects_reassessment
  + thought_action_proposal into ONE Central-governed family;
* this family has NO LLM member — every member is rules/DB-driven and runs in the
  UNCONDITIONAL tier and self-throttles on its own cadence; the family's one gate
  is fail-open (no gated signals → always fires);
* task_worker is LOAD-BEARING infrastructure: it is FIRST in the unconditional tier
  and MUST drain the queue EVERY family tick (gate on AND off, even if the gated
  family tick blows up) — no self-throttle, and no failing sibling can block it;
* my_projects_watchdog (240-min) and life_projects_reassessment (1440-min) self-
  throttle on the cadence the family gives them; thought_action_proposal self-
  throttles intrinsically on the latest thought-stream fragment;
* a member error never crashes the family; the tick never raises;
* the 4 old daemons are RETIRED and cluster_projects is registered LIVE.

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
    "task_worker": ("core.services.task_worker", "tick_task_worker"),
    "my_projects_watchdog": ("core.services.my_projects", "tick_my_projects_watchdog"),
    "life_projects_reassessment": ("core.services.life_projects", "tick_life_projects_reassessment"),
    "thought_action_proposal": (
        "core.services.thought_action_proposal_daemon",
        "tick_thought_action_proposal_daemon",
    ),
}

_SNAP = {"latest_fragment": "jeg burde måske rydde op i mine noter"}


def _reset_throttle() -> None:
    """Clear the family's per-member self-throttle so members are ready to run."""
    cdmf._PROJECTS_THROTTLE.clear()


def _patch_member_ticks(stack: ExitStack) -> dict[str, MagicMock]:
    mocks: dict[str, MagicMock] = {}
    for member, (mod, fn) in _MEMBER_TICKS.items():
        m = MagicMock(return_value={"status": "ok", "member": member})
        stack.enter_context(patch(f"{mod}.{fn}", m))
        mocks[member] = m
    return mocks


def _patch_env(stack: ExitStack, *, gate_fires: bool) -> None:
    stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
    stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=gate_fires))
    stack.enter_context(patch("core.services.central_core.central"))
    stack.enter_context(patch.object(cdmf, "_collect_projects_snapshot", return_value=dict(_SNAP)))


# ---------------------------------------------------------------------------
# Structure: no LLM/gated member; task_worker first in the unconditional tier
# ---------------------------------------------------------------------------


def test_projects_family_has_no_gated_llm_member():
    fam = cdmf.build_projects_family()
    assert fam.family_name == "cluster_projects"
    assert fam.members == [], "projects family is all-rules — the gated tier is empty"


def test_task_worker_is_first_unconditional_member():
    names = [name for name, _ in cdmf._PROJECTS_UNCONDITIONAL]
    assert names[0] == "task_worker", "load-bearing task_worker must run FIRST"
    assert set(names) == {
        "task_worker",
        "my_projects_watchdog",
        "life_projects_reassessment",
        "thought_action_proposal",
    }


# ---------------------------------------------------------------------------
# task_worker drains every tick — gate ON and gate OFF (load-bearing paramount)
# ---------------------------------------------------------------------------


def test_task_worker_drains_when_gate_fires():
    _reset_throttle()
    with ExitStack() as stack:
        mocks = _patch_member_ticks(stack)
        _patch_env(stack, gate_fires=True)
        result = cdmf.tick_cluster_projects()

    mocks["task_worker"].assert_called_once_with(budget=3)
    assert "task_worker" in result["members_ran"]
    assert result["outputs"]["task_worker"] == {"status": "ok", "member": "task_worker"}


def test_task_worker_drains_even_when_gate_does_not_fire():
    """The family gate must NEVER be able to block the load-bearing queue drain."""
    _reset_throttle()
    with ExitStack() as stack:
        mocks = _patch_member_ticks(stack)
        _patch_env(stack, gate_fires=False)
        result = cdmf.tick_cluster_projects()

    mocks["task_worker"].assert_called_once_with(budget=3)
    assert "task_worker" in result["members_ran"]


def test_task_worker_drains_even_if_gated_family_tick_raises():
    """Strongest guarantee: even a catastrophic family-gate tick failure cannot
    skip the queue drain — the unconditional tier runs regardless."""
    _reset_throttle()
    broken = MagicMock(side_effect=RuntimeError("gate boom"))
    fake_family = MagicMock()
    fake_family.tick = broken
    with ExitStack() as stack:
        mocks = _patch_member_ticks(stack)
        stack.enter_context(patch("core.services.central_core.central"))
        stack.enter_context(patch.object(cdmf, "_collect_projects_snapshot", return_value=dict(_SNAP)))
        stack.enter_context(patch.object(cdmf, "projects_family", return_value=fake_family))
        result = cdmf.tick_cluster_projects()

    mocks["task_worker"].assert_called_once_with(budget=3)
    assert "task_worker" in result["members_ran"]
    assert "__gated__" in result["member_errors"]
    assert "boom" in result["member_errors"]["__gated__"]


def test_task_worker_drains_on_every_tick_no_throttle():
    """task_worker has NO self-throttle: it drains on each of N consecutive ticks."""
    _reset_throttle()
    with ExitStack() as stack:
        mocks = _patch_member_ticks(stack)
        _patch_env(stack, gate_fires=True)
        for _ in range(3):
            cdmf.tick_cluster_projects()

    assert mocks["task_worker"].call_count == 3


# ---------------------------------------------------------------------------
# Error isolation — a failing sibling never blocks task_worker
# ---------------------------------------------------------------------------


def test_failing_sibling_never_blocks_task_worker():
    _reset_throttle()
    with ExitStack() as stack:
        mocks = _patch_member_ticks(stack)
        mocks["my_projects_watchdog"].side_effect = RuntimeError("watchdog boom")
        _patch_env(stack, gate_fires=True)
        result = cdmf.tick_cluster_projects()

    # sibling error is isolated ...
    assert "my_projects_watchdog" in result["member_errors"]
    assert "boom" in result["member_errors"]["my_projects_watchdog"]
    # ... but task_worker drained anyway, and the other siblings still ran
    mocks["task_worker"].assert_called_once_with(budget=3)
    assert "task_worker" in result["members_ran"]
    assert "life_projects_reassessment" in result["members_ran"]
    assert "thought_action_proposal" in result["members_ran"]


def test_task_worker_error_isolated_and_family_survives():
    _reset_throttle()
    with ExitStack() as stack:
        mocks = _patch_member_ticks(stack)
        mocks["task_worker"].side_effect = RuntimeError("worker boom")
        _patch_env(stack, gate_fires=True)
        result = cdmf.tick_cluster_projects()

    assert "task_worker" in result["member_errors"]
    assert "boom" in result["member_errors"]["task_worker"]
    # siblings still ran despite task_worker's own error
    assert "my_projects_watchdog" in result["members_ran"]
    assert "thought_action_proposal" in result["members_ran"]


# ---------------------------------------------------------------------------
# Each member self-throttles on its own cadence
# ---------------------------------------------------------------------------


def test_my_projects_watchdog_self_throttles_240min():
    _reset_throttle()
    with ExitStack() as stack:
        mocks = _patch_member_ticks(stack)
        _patch_env(stack, gate_fires=True)
        cdmf.tick_cluster_projects()   # first tick: throttle ready → runs
        cdmf.tick_cluster_projects()   # immediate second tick: throttled

    assert mocks["my_projects_watchdog"].call_count == 1
    # task_worker (no throttle) drained on BOTH ticks
    assert mocks["task_worker"].call_count == 2


def test_life_projects_reassessment_self_throttles_1440min():
    _reset_throttle()
    with ExitStack() as stack:
        mocks = _patch_member_ticks(stack)
        _patch_env(stack, gate_fires=True)
        cdmf.tick_cluster_projects()   # first tick: runs
        cdmf.tick_cluster_projects()   # immediate second tick: throttled

    assert mocks["life_projects_reassessment"].call_count == 1
    assert mocks["life_projects_reassessment"].call_args.kwargs.get("trigger") == "heartbeat"


def test_throttled_member_still_recorded_as_run():
    """A throttled member returns a self-throttle marker but still counts as run so
    the heartbeat sees it participated (parity with the other families)."""
    _reset_throttle()
    with ExitStack() as stack:
        _patch_member_ticks(stack)
        _patch_env(stack, gate_fires=True)
        cdmf.tick_cluster_projects()
        result = cdmf.tick_cluster_projects()  # second tick → members throttled

    assert result["outputs"]["my_projects_watchdog"]["status"] == "throttled"
    assert result["outputs"]["life_projects_reassessment"]["status"] == "throttled"
    assert "my_projects_watchdog" in result["members_ran"]


# ---------------------------------------------------------------------------
# thought_action_proposal — fragment-driven (intrinsic self-throttle)
# ---------------------------------------------------------------------------


def test_thought_action_runs_on_latest_fragment():
    _reset_throttle()
    with ExitStack() as stack:
        mocks = _patch_member_ticks(stack)
        _patch_env(stack, gate_fires=True)
        cdmf.tick_cluster_projects()

    mocks["thought_action_proposal"].assert_called_once_with(_SNAP["latest_fragment"])


def test_thought_action_skips_without_fragment():
    _reset_throttle()
    with ExitStack() as stack:
        mocks = _patch_member_ticks(stack)
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=True))
        stack.enter_context(patch("core.services.central_core.central"))
        stack.enter_context(patch.object(cdmf, "_collect_projects_snapshot", return_value={"latest_fragment": ""}))
        result = cdmf.tick_cluster_projects()

    mocks["thought_action_proposal"].assert_not_called()
    assert result["outputs"]["thought_action_proposal"]["skip_reason"] == "no_fragment"
    # task_worker still drained
    mocks["task_worker"].assert_called_once_with(budget=3)


# ---------------------------------------------------------------------------
# Load-bearing outputs preserved + all members in one tick
# ---------------------------------------------------------------------------


def test_all_members_run_in_one_tick():
    _reset_throttle()
    with ExitStack() as stack:
        mocks = _patch_member_ticks(stack)
        _patch_env(stack, gate_fires=True)
        result = cdmf.tick_cluster_projects()

    assert set(result["members_ran"]) == {
        "task_worker",
        "my_projects_watchdog",
        "life_projects_reassessment",
        "thought_action_proposal",
    }
    for m in mocks.values():
        assert m.call_count == 1


def test_snapshot_collects_latest_fragment():
    with patch("core.services.thought_stream_daemon.get_latest_thought_fragment", return_value="en tanke"):
        snap = cdmf._collect_projects_snapshot()
    assert snap["latest_fragment"] == "en tanke"


# ---------------------------------------------------------------------------
# Self-safety
# ---------------------------------------------------------------------------


def test_entrypoint_never_raises_on_broken_family():
    _reset_throttle()
    with ExitStack() as stack:
        _patch_member_ticks(stack)
        stack.enter_context(patch("core.services.central_core.central"))
        stack.enter_context(patch.object(cdmf, "projects_family", side_effect=RuntimeError("family down")))
        stack.enter_context(patch.object(cdmf, "_collect_projects_snapshot", return_value=dict(_SNAP)))
        result = cdmf.tick_cluster_projects()

    assert result["family"] == "cluster_projects"
    assert "__gated__" in result["member_errors"]
    # even with the family object broken, task_worker still drained
    assert "task_worker" in result["members_ran"]


def test_entrypoint_survives_broken_snapshot():
    _reset_throttle()
    with ExitStack() as stack:
        mocks = _patch_member_ticks(stack)
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=True))
        stack.enter_context(patch("core.services.central_core.central"))
        stack.enter_context(patch.object(cdmf, "_collect_projects_snapshot", side_effect=RuntimeError("snap boom")))
        result = cdmf.tick_cluster_projects()

    # snapshot failure degrades to a neutral snap; task_worker still drains
    mocks["task_worker"].assert_called_once_with(budget=3)
    assert result["family"] == "cluster_projects"


def test_entrypoint_runs_live_by_default():
    _reset_throttle()
    with ExitStack() as stack:
        _patch_member_ticks(stack)
        _patch_env(stack, gate_fires=True)
        result = cdmf.tick_cluster_projects()
    assert result["shadow"] is False


# ---------------------------------------------------------------------------
# Registration + retirement in daemon_manager
# ---------------------------------------------------------------------------


def test_cluster_projects_registered_live():
    from core.services import daemon_manager as dm

    assert "cluster_projects" in dm.get_daemon_names()
    states = {d["name"]: d for d in dm.get_all_daemon_states()}
    entry = states["cluster_projects"]
    assert entry["enabled"] is True
    assert "projects" in entry["description"]


def test_four_old_daemons_retired():
    from core.services import daemon_manager as dm

    retired = [
        "task_worker",
        "my_projects_watchdog",
        "life_projects_reassessment",
        "thought_action_proposal",
    ]
    with patch.object(dm, "_load_state", return_value={}):
        for name in retired:
            assert dm._REGISTRY[name].get("default_enabled") is False, f"{name} must default disabled"
            assert dm._REGISTRY[name].get("retired") == "2026-07-15", f"{name} missing retired marker"
            assert "cluster_projects" in dm._REGISTRY[name]["description"], f"{name} desc must point to cluster_projects"
            assert dm.is_enabled(name) is False, f"{name} must be disabled (retired)"
