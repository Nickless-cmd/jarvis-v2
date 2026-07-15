"""E2E tests for the relation cluster-daemon family #8.

Consolidation contract:
* the family runs its event-gate ONCE for the LLM tier — a single gated member
  (user_model, a former per-daemon should_generative_fire call) now sits behind
  the family's one should_generative_fire("cluster_relation", …) call;
* when the gate fires, the gated member dispatches to the SAME tick the old daemon
  used, with skip_event_gate=True (its 10-min cadence self-throttle still applies)
  and the LLM theory-of-mind interpretation is preserved (spec correction #3);
* the TWO non-LLM members (communication_guard, relation_map_refresh) run
  UNCONDITIONALLY every tick, independent of the gate, each self-throttling on its
  own internal cadence;
* a member error never crashes the family; the tick never raises;
* the 3 old daemons are RETIRED and cluster_relation is registered LIVE;
* the load-bearing surfaces (user-model summary, comm-guard cleanup, relation-map
  refresh) are preserved.

Patches target the NEW module cluster_daemon_families (not cluster_daemon).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import core.services.cluster_daemon_families as cdmf

# The single GATED LLM member and the (module, tick-fn) it dispatches to.
_GATED_TICK = ("core.services.user_model_daemon", "tick_user_model_daemon")

# The two non-LLM members and the (module, fn) each runs unconditionally.
_NONLLM_TICKS = {
    "communication_guard": ("core.services.communication_guard_daemon", "tick_communication_guard_daemon"),
    "relation_map_refresh": ("core.services.relation_map", "tick_relation_map_refresh"),
}

_SNAP = {
    "user_messages": ["hej?", "hvordan går det med projektet?", "kan du hjælpe?"],
    "message_count": 3.0,
    "avg_message_length": 25.0,
    "question_ratio": 1.0,
}


def _patch_gated_tick(stack: ExitStack) -> MagicMock:
    mod, fn = _GATED_TICK
    m = MagicMock(return_value={"generated": True, "summary": "brugeren virker nysgerrig"})
    stack.enter_context(patch(f"{mod}.{fn}", m))
    return m


def _patch_nonllm_ticks(stack: ExitStack) -> dict[str, MagicMock]:
    mocks: dict[str, MagicMock] = {}
    for member, (mod, fn) in _NONLLM_TICKS.items():
        m = MagicMock(return_value={"status": "ok", "member": member})
        stack.enter_context(patch(f"{mod}.{fn}", m))
        mocks[member] = m
    return mocks


# ---------------------------------------------------------------------------
# ONE gate for the whole family's LLM tier (the load-reduction invariant)
# ---------------------------------------------------------------------------


def test_relation_family_gates_once():
    """The gated LLM tier consults should_generative_fire exactly ONCE."""
    fam = cdmf.build_relation_family()
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


def test_build_relation_family_declares_single_gated_member():
    fam = cdmf.build_relation_family()
    assert fam.family_name == "cluster_relation"
    assert {m.name for m in fam.members} == {"user_model"}


def test_family_gate_receives_user_model_namespaced_signals():
    fam = cdmf.build_relation_family()
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

    assert seen["name"] == "cluster_relation"
    assert any(k.startswith("user_model:") for k in seen["signals"]), "gated member signals missing from the ONE gate"


# ---------------------------------------------------------------------------
# Dispatch — gated member runs iff the family gate fires
# ---------------------------------------------------------------------------


def test_fired_family_invokes_user_model_with_skip_gate():
    fam = cdmf.build_relation_family()
    with ExitStack() as stack:
        m = _patch_gated_tick(stack)
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=True))
        stack.enter_context(patch("core.services.central_core.central"))
        result = fam.tick(_SNAP, shadow=False)

    assert result["members_ran"] == ["user_model"]
    assert m.call_count == 1
    # the family already gated → the daemon's own event-gate is bypassed
    assert m.call_args.kwargs.get("skip_event_gate") is True
    # the collected user messages are forwarded so gen sees what the gate weighed
    assert m.call_args.args[0] == _SNAP["user_messages"]


def test_gate_skip_runs_no_user_model_generation():
    fam = cdmf.build_relation_family()
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
        stack.enter_context(patch.object(cdmf, "_collect_relation_snapshot", return_value=_SNAP))
        result = cdmf.tick_cluster_relation()

    assert nonllm["communication_guard"].call_count == 1
    assert nonllm["relation_map_refresh"].call_count == 1
    assert "communication_guard" in result["members_ran"]
    assert "relation_map_refresh" in result["members_ran"]


def test_nonllm_members_run_even_when_gate_does_not_fire():
    """The non-LLM members must run every tick regardless of the generative gate."""
    with ExitStack() as stack:
        gated = _patch_gated_tick(stack)
        nonllm = _patch_nonllm_ticks(stack)
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=False))
        stack.enter_context(patch("core.services.central_core.central"))
        stack.enter_context(patch.object(cdmf, "_collect_relation_snapshot", return_value=_SNAP))
        result = cdmf.tick_cluster_relation()

    # generative gate blocked the LLM member ...
    assert result["fired"] is False
    assert gated.call_count == 0
    # ... but both non-LLM members ran anyway
    assert nonllm["communication_guard"].call_count == 1
    assert nonllm["relation_map_refresh"].call_count == 1
    assert "communication_guard" in result["members_ran"]
    assert "relation_map_refresh" in result["members_ran"]


def test_all_members_run_in_one_tick():
    with ExitStack() as stack:
        gated = _patch_gated_tick(stack)
        nonllm = _patch_nonllm_ticks(stack)
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=True))
        stack.enter_context(patch("core.services.central_core.central"))
        stack.enter_context(patch.object(cdmf, "_collect_relation_snapshot", return_value=_SNAP))
        result = cdmf.tick_cluster_relation()

    assert set(result["members_ran"]) == {"user_model", "communication_guard", "relation_map_refresh"}
    assert gated.call_count == 1
    assert nonllm["communication_guard"].call_count == 1
    assert nonllm["relation_map_refresh"].call_count == 1


# ---------------------------------------------------------------------------
# Each member self-throttles on its OWN internal cadence
# ---------------------------------------------------------------------------


def test_user_model_member_self_throttles_via_cadence_gate():
    """user_model keeps its 10-min cadence self-throttle even with
    skip_event_gate=True — the family only replaces the per-daemon event-gate, not
    the cadence guard. Proves the family relies on the member's internal throttle."""
    from datetime import UTC, datetime

    import core.services.user_model_daemon as umd

    prev = umd._last_tick_at
    try:
        umd._last_tick_at = datetime.now(UTC)  # inside the 10-min cadence window
        out = cdmf._relation_user_model_live(_SNAP)
        # cadence-gate short-circuits BEFORE any LLM generation
        assert out.get("generated") is False
        assert out.get("skip_reason") == "cadence_gate"
    finally:
        umd._last_tick_at = prev


def test_relation_map_refresh_forwarded_as_rules_member():
    """relation_map_refresh is a rules-based (no-LLM) member dispatched to the old
    tick with the heartbeat trigger — no should_generative_fire involved."""
    with ExitStack() as stack:
        m = MagicMock(return_value={"status": "ok", "refreshed": 1})
        stack.enter_context(patch("core.services.relation_map.tick_relation_map_refresh", m))
        out = cdmf._relation_map_refresh_live(_SNAP)

    assert out["status"] == "ok"
    assert m.call_args.kwargs.get("trigger") == "heartbeat"


# ---------------------------------------------------------------------------
# Load-bearing outputs preserved
# ---------------------------------------------------------------------------


def test_nonllm_outputs_recorded_in_family_result():
    """The non-LLM members' outputs are echoed into the family result so the
    heartbeat/consumers still see them."""
    with ExitStack() as stack:
        _patch_gated_tick(stack)
        nonllm = _patch_nonllm_ticks(stack)
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=False))
        stack.enter_context(patch("core.services.central_core.central"))
        stack.enter_context(patch.object(cdmf, "_collect_relation_snapshot", return_value=_SNAP))
        result = cdmf.tick_cluster_relation()

    assert result["outputs"]["communication_guard"] == {"status": "ok", "member": "communication_guard"}
    assert result["outputs"]["relation_map_refresh"] == {"status": "ok", "member": "relation_map_refresh"}
    assert nonllm["communication_guard"].call_count == 1


def test_snapshot_collects_user_messages_load_bearing():
    """The family snapshot collector fetches recent visible user messages and
    derives the gate signals, so the user_model surface stays fed."""
    with ExitStack() as stack:
        runs = [
            {"lane": "primary", "text_preview": "hej jarvis, kan du hjælpe?"},
            {"lane": "primary", "text_preview": "hvad synes du?"},
            {"lane": "internal", "text_preview": "ignoreret non-visible lane"},
        ]
        stack.enter_context(patch("core.runtime.db.recent_visible_runs", return_value=runs))
        snap = cdmf._collect_relation_snapshot()

    assert snap["message_count"] == 2.0  # only the two visible/primary lanes
    assert snap["question_ratio"] == 1.0
    assert snap["user_messages"] == ["hej jarvis, kan du hjælpe?", "hvad synes du?"]


# ---------------------------------------------------------------------------
# Self-safety
# ---------------------------------------------------------------------------


def test_nonllm_error_isolated_and_family_survives():
    with ExitStack() as stack:
        gated = _patch_gated_tick(stack)
        nonllm = _patch_nonllm_ticks(stack)
        nonllm["communication_guard"].side_effect = RuntimeError("guard boom")
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=True))
        stack.enter_context(patch("core.services.central_core.central"))
        stack.enter_context(patch.object(cdmf, "_collect_relation_snapshot", return_value=_SNAP))
        result = cdmf.tick_cluster_relation()

    assert "communication_guard" in result["member_errors"]
    assert "boom" in result["member_errors"]["communication_guard"]
    # the gated member + the other non-LLM sibling still ran despite the error
    assert gated.call_count == 1
    assert "user_model" in result["members_ran"]
    assert "relation_map_refresh" in result["members_ran"]


def test_user_model_error_does_not_crash_family():
    with ExitStack() as stack:
        m = _patch_gated_tick(stack)
        m.side_effect = RuntimeError("user_model exploded")
        nonllm = _patch_nonllm_ticks(stack)
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=True))
        stack.enter_context(patch("core.services.central_core.central"))
        stack.enter_context(patch.object(cdmf, "_collect_relation_snapshot", return_value=_SNAP))
        result = cdmf.tick_cluster_relation()

    assert "user_model" in result["member_errors"]
    assert "exploded" in result["member_errors"]["user_model"]
    # the non-LLM siblings still ran despite the gated member's error
    assert nonllm["communication_guard"].call_count == 1
    assert nonllm["relation_map_refresh"].call_count == 1


def test_entrypoint_never_raises_on_broken_family():
    with patch.object(cdmf, "relation_family", side_effect=RuntimeError("family down")), \
         patch.object(cdmf, "_collect_relation_snapshot", return_value=_SNAP):
        result = cdmf.tick_cluster_relation()
    assert result["family"] == "cluster_relation"
    assert result["gate_calls"] == 1
    assert "__entry__" in result["member_errors"]


def test_entrypoint_runs_live_by_default():
    """tick_cluster_relation defaults to LIVE (shadow=False) so it produces."""
    with ExitStack() as stack:
        gated = _patch_gated_tick(stack)
        _patch_nonllm_ticks(stack)
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=True))
        stack.enter_context(patch("core.services.central_core.central"))
        stack.enter_context(patch.object(cdmf, "_collect_relation_snapshot", return_value=_SNAP))
        result = cdmf.tick_cluster_relation()

    assert result["shadow"] is False
    assert gated.call_count == 1


# ---------------------------------------------------------------------------
# Registration + retirement in daemon_manager
# ---------------------------------------------------------------------------


def test_cluster_relation_registered_live():
    from core.services import daemon_manager as dm

    assert "cluster_relation" in dm.get_daemon_names()
    states = {d["name"]: d for d in dm.get_all_daemon_states()}
    entry = states["cluster_relation"]
    assert entry["enabled"] is True
    assert "relation" in entry["description"]


def test_three_old_daemons_retired():
    from core.services import daemon_manager as dm

    retired = ["user_model", "communication_guard", "relation_map_refresh"]
    with patch.object(dm, "_load_state", return_value={}):
        for name in retired:
            assert dm._REGISTRY[name].get("default_enabled") is False, f"{name} must default disabled"
            assert dm._REGISTRY[name].get("retired") == "2026-07-15", f"{name} missing retired marker"
            assert "cluster_relation" in dm._REGISTRY[name]["description"], f"{name} desc must point to cluster_relation"
            assert dm.is_enabled(name) is False, f"{name} must be disabled (retired)"
