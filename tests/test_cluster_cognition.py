"""E2E tests for the cognition cluster-daemon family #5 (spec 2026-07-14).

Consolidation contract:
* the family runs its event-gate ONCE for the LLM tier — a single gated member
  (pattern_counterfactual, a former blind-timer LLM) now sits behind the family's
  one should_generative_fire("cluster_cognition", …) call;
* when the gate fires, the gated member dispatches to the SAME generation function
  the old daemon used, so counterfactual.pattern_what_if events keep filling;
* the THREE non-LLM members (causal_inference, dream_insight, active_sensing) run
  UNCONDITIONALLY every tick, independent of the family generative gate, each
  self-throttling on its own internal cadence/dedupe;
* causal_edges (causal_inference) + the dream-insight cache + the active_sensing
  surface are load-bearing and must keep flowing to their consumers;
* a member error never crashes the family; the tick never raises;
* the 4 old cognition daemons are RETIRED and cluster_cognition is registered LIVE.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import core.services.cluster_daemon as cdm

# The single GATED LLM member and the (module, tick-fn) it dispatches to.
_GATED_TICK = ("core.services.pattern_counterfactual_daemon", "tick_pattern_counterfactual_daemon")

# The 3 NON-LLM members and the (module, tick-fn) each runs unconditionally.
_NONLLM_TICKS = {
    "causal_inference": ("core.services.causal_inference_daemon", "tick_causal_inference_daemon"),
    "dream_insight": ("core.services.dream_insight_daemon", "tick_dream_insight_daemon"),
    "active_sensing": ("core.services.active_sensing_daemon", "tick_active_sensing_daemon"),
}

_SNAP = {"top_patterns": [{"parent_kind": "a", "child_kind": "b", "count": 5}], "pattern_count": 1, "pattern_occurrences": 5.0}


def _patch_gated_tick(stack: ExitStack) -> MagicMock:
    mod, fn = _GATED_TICK
    m = MagicMock(return_value={"ran": True, "written": 1})
    stack.enter_context(patch(f"{mod}.{fn}", m))
    return m


def _patch_nonllm_ticks(stack: ExitStack) -> dict[str, MagicMock]:
    mocks: dict[str, MagicMock] = {}
    for member, (mod, fn) in _NONLLM_TICKS.items():
        m = MagicMock(return_value={"ran": True, "member": member})
        stack.enter_context(patch(f"{mod}.{fn}", m))
        mocks[member] = m
    # dream_insight's live() gathers a candidate from dream_articulation first —
    # stub the surface so the member actually invokes its tick.
    stack.enter_context(patch(
        "core.services.dream_articulation.build_dream_articulation_surface",
        return_value={"summary": {"latest_signal_id": "sig-1", "latest_summary": "en drøm"}},
    ))
    return mocks


# ---------------------------------------------------------------------------
# ONE gate for the whole family's LLM tier (the load-reduction invariant)
# ---------------------------------------------------------------------------


def test_cognition_family_gates_once():
    """The gated LLM tier consults should_generative_fire exactly ONCE."""
    fam = cdm.build_cognition_family()
    calls = {"n": 0}

    def _fire(name, signals, **kw):
        calls["n"] += 1
        return True

    with ExitStack() as stack:
        _patch_gated_tick(stack)
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", side_effect=_fire))
        stack.enter_context(patch("core.services.central_core.central"))
        result = fam.tick(_SNAP, shadow=False)

    assert calls["n"] == 1, "family must gate ONCE for the LLM tier"
    assert result["gate_calls"] == 1
    assert result["fired"] is True


def test_family_gate_receives_pattern_cf_namespaced_signals():
    fam = cdm.build_cognition_family()
    seen: dict = {}

    def _fire(name, signals, **kw):
        seen["name"] = name
        seen["signals"] = dict(signals)
        return True

    with ExitStack() as stack:
        _patch_gated_tick(stack)
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", side_effect=_fire))
        stack.enter_context(patch("core.services.central_core.central"))
        fam.tick(_SNAP, shadow=False)

    assert seen["name"] == "cluster_cognition"
    assert any(k.startswith("pattern_counterfactual:") for k in seen["signals"]), "gated member signals missing from the ONE gate"


def test_build_cognition_family_declares_single_gated_member():
    fam = cdm.build_cognition_family()
    assert fam.family_name == "cluster_cognition"
    assert {m.name for m in fam.members} == {"pattern_counterfactual"}


# ---------------------------------------------------------------------------
# Dispatch — gated member runs iff the family gate fires
# ---------------------------------------------------------------------------


def test_fired_family_invokes_gated_member():
    fam = cdm.build_cognition_family()
    with ExitStack() as stack:
        m = _patch_gated_tick(stack)
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=True))
        stack.enter_context(patch("core.services.central_core.central"))
        result = fam.tick(_SNAP, shadow=False)

    assert result["members_ran"] == ["pattern_counterfactual"]
    assert m.call_count == 1


def test_gate_skip_runs_no_gated_generation():
    fam = cdm.build_cognition_family()
    with ExitStack() as stack:
        m = _patch_gated_tick(stack)
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=False))
        stack.enter_context(patch("core.services.central_core.central"))
        result = fam.tick(_SNAP, shadow=False)

    assert result["fired"] is False
    assert result["members_ran"] == []
    assert m.call_count == 0


# ---------------------------------------------------------------------------
# Non-LLM members run UNCONDITIONALLY (via the entry-point), gate or no gate
# ---------------------------------------------------------------------------


def test_nonllm_members_run_when_gate_fires():
    with ExitStack() as stack:
        _patch_gated_tick(stack)
        nonllm = _patch_nonllm_ticks(stack)
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=True))
        stack.enter_context(patch("core.services.central_core.central"))
        stack.enter_context(patch.object(cdm, "_collect_cognition_snapshot", return_value=_SNAP))
        result = cdm.tick_cluster_cognition()

    for member, m in nonllm.items():
        assert m.call_count == 1, f"{member} must run"
        assert member in result["members_ran"]


def test_nonllm_members_run_even_when_gate_does_not_fire():
    """The load-bearing rules — causal inference, dream-insight persist, active
    sensing — must run every tick regardless of the generative family gate."""
    with ExitStack() as stack:
        gated = _patch_gated_tick(stack)
        nonllm = _patch_nonllm_ticks(stack)
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=False))
        stack.enter_context(patch("core.services.central_core.central"))
        stack.enter_context(patch.object(cdm, "_collect_cognition_snapshot", return_value=_SNAP))
        result = cdm.tick_cluster_cognition()

    # generative gate blocked the LLM member ...
    assert result["fired"] is False
    assert gated.call_count == 0
    # ... but the 3 non-LLM members ran anyway
    for member, m in nonllm.items():
        assert m.call_count == 1, f"{member} must run unconditionally"
        assert member in result["members_ran"]


def test_dream_insight_member_passes_articulation_signal():
    """dream_insight is signal-driven: the member gathers signal_id/summary from
    dream_articulation and forwards them to the old persist tick."""
    with ExitStack() as stack:
        _patch_gated_tick(stack)
        nonllm = _patch_nonllm_ticks(stack)
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=False))
        stack.enter_context(patch("core.services.central_core.central"))
        stack.enter_context(patch.object(cdm, "_collect_cognition_snapshot", return_value=_SNAP))
        cdm.tick_cluster_cognition()

    di = nonllm["dream_insight"]
    assert di.call_args.kwargs.get("signal_id") == "sig-1"
    assert di.call_args.kwargs.get("signal_summary") == "en drøm"


# ---------------------------------------------------------------------------
# Each member self-throttles on its OWN internal cadence
# ---------------------------------------------------------------------------


def test_members_self_throttle_when_cadence_not_elapsed():
    """causal_inference (15min) and pattern_counterfactual (60min) return their
    throttled marker when their own cadence window has not elapsed."""
    from datetime import UTC, datetime
    import core.services.causal_inference_daemon as cid
    import core.services.pattern_counterfactual_daemon as pcd

    now = datetime.now(UTC)
    cid._last_tick_at = now
    pcd._last_tick_at = now

    assert cid.tick_causal_inference_daemon() == {"ran": False}
    ns = pcd.tick_pattern_counterfactual_daemon()
    assert ns["ran"] is False and ns["reason"] == "cadence-not-elapsed"


# ---------------------------------------------------------------------------
# Load-bearing outputs preserved
# ---------------------------------------------------------------------------


def test_dream_insight_cache_flows_through_cluster():
    """When the family runs, the dream_insight member fills the module cache that
    central_inner_life_digest / signal_surface_router read via get_latest_*."""
    import core.services.dream_insight_daemon as did

    with ExitStack() as stack:
        _patch_gated_tick(stack)
        stack.enter_context(patch("core.services.central_core.central"))
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=False))
        stack.enter_context(patch(
            "core.services.dream_articulation.build_dream_articulation_surface",
            return_value={"summary": {"latest_signal_id": "sig-xyz", "latest_summary": "jeg drømte om lys"}},
        ))
        # stub causal + active_sensing so the test isolates dream_insight
        stack.enter_context(patch("core.services.causal_inference_daemon.tick_causal_inference_daemon", MagicMock(return_value={})))
        stack.enter_context(patch("core.services.active_sensing_daemon.tick_active_sensing_daemon", MagicMock(return_value={})))
        stack.enter_context(patch.object(did, "insert_private_brain_record"))
        stack.enter_context(patch.object(did, "event_bus"))
        did._last_insight = ""
        did._last_persisted_signal_id = ""
        stack.enter_context(patch.object(cdm, "_collect_cognition_snapshot", return_value=_SNAP))
        cdm.tick_cluster_cognition()

    assert did.get_latest_dream_insight() == "jeg drømte om lys"


# ---------------------------------------------------------------------------
# Self-safety
# ---------------------------------------------------------------------------


def test_gated_member_error_does_not_crash_family():
    with ExitStack() as stack:
        m = _patch_gated_tick(stack)
        m.side_effect = RuntimeError("pattern exploded")
        _patch_nonllm_ticks(stack)
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=True))
        stack.enter_context(patch("core.services.central_core.central"))
        stack.enter_context(patch.object(cdm, "_collect_cognition_snapshot", return_value=_SNAP))
        result = cdm.tick_cluster_cognition()

    assert "pattern_counterfactual" in result["member_errors"]
    assert "exploded" in result["member_errors"]["pattern_counterfactual"]
    # the 3 non-LLM siblings still ran despite the gated member's error
    assert set(_NONLLM_TICKS).issubset(set(result["members_ran"]))


def test_nonllm_member_error_isolated_and_siblings_still_run():
    with ExitStack() as stack:
        _patch_gated_tick(stack)
        nonllm = _patch_nonllm_ticks(stack)
        nonllm["causal_inference"].side_effect = RuntimeError("causal boom")
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=True))
        stack.enter_context(patch("core.services.central_core.central"))
        stack.enter_context(patch.object(cdm, "_collect_cognition_snapshot", return_value=_SNAP))
        result = cdm.tick_cluster_cognition()

    assert "causal_inference" in result["member_errors"]
    assert "boom" in result["member_errors"]["causal_inference"]
    # sibling non-LLM members still ran despite the other's error
    assert nonllm["dream_insight"].call_count == 1
    assert nonllm["active_sensing"].call_count == 1
    assert "active_sensing" in result["members_ran"]


def test_entrypoint_never_raises_on_broken_family():
    with patch.object(cdm, "cognition_family", side_effect=RuntimeError("family down")), \
         patch.object(cdm, "_collect_cognition_snapshot", return_value=_SNAP):
        result = cdm.tick_cluster_cognition()
    assert result["family"] == "cluster_cognition"
    assert result["gate_calls"] == 1
    assert "__entry__" in result["member_errors"]


def test_entrypoint_runs_live_by_default():
    """tick_cluster_cognition defaults to LIVE (shadow=False) so it produces."""
    with ExitStack() as stack:
        gated = _patch_gated_tick(stack)
        _patch_nonllm_ticks(stack)
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=True))
        stack.enter_context(patch("core.services.central_core.central"))
        stack.enter_context(patch.object(cdm, "_collect_cognition_snapshot", return_value=_SNAP))
        result = cdm.tick_cluster_cognition()

    assert result["shadow"] is False
    assert gated.call_count == 1


# ---------------------------------------------------------------------------
# Registration + retirement in daemon_manager
# ---------------------------------------------------------------------------


def test_cluster_cognition_registered_live():
    from core.services import daemon_manager as dm

    assert "cluster_cognition" in dm.get_daemon_names()
    states = {d["name"]: d for d in dm.get_all_daemon_states()}
    entry = states["cluster_cognition"]
    assert entry["enabled"] is True
    assert "cognition" in entry["description"]


def test_four_old_cognition_daemons_retired():
    from core.services import daemon_manager as dm

    retired = ["causal_inference", "pattern_counterfactual", "dream_insight", "active_sensing"]
    with patch.object(dm, "_load_state", return_value={}):
        for name in retired:
            assert dm._REGISTRY[name].get("default_enabled") is False, f"{name} must default disabled"
            assert dm._REGISTRY[name].get("retired") == "2026-07-15", f"{name} missing retired marker"
            assert "cluster_cognition" in dm._REGISTRY[name]["description"], f"{name} desc must point to cluster_cognition"
            assert dm.is_enabled(name) is False, f"{name} must be disabled (retired)"
