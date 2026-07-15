"""E2E tests for the aesthetic/curiosity cluster-daemon family #7.

Consolidation contract:
* the family runs its event-gate ONCE for the LLM tier — a single gated member
  (aesthetic_taste, a former per-daemon should_generative_fire call) now sits
  behind the family's one should_generative_fire("cluster_aesthetic", …) call;
* when the gate fires, the gated member dispatches to the SAME tick the old daemon
  used, with skip_event_gate=True (its motif-threshold + 30-min time-gate
  self-throttle still apply);
* the ONE non-LLM member (curiosity) runs UNCONDITIONALLY every tick, independent
  of the gate, self-throttling on its own 5-min cadence;
* a member error never crashes the family; the tick never raises;
* the 2 old daemons are RETIRED and cluster_aesthetic is registered LIVE;
* the load-bearing surfaces (taste insight, curiosity signal) are preserved.

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
_GATED_TICK = ("core.services.aesthetic_taste_daemon", "tick_taste_daemon")

# The ONE non-LLM member and the (module, fn) it runs unconditionally.
_NONLLM_TICKS = {
    "curiosity": ("core.services.curiosity_daemon", "tick_curiosity_daemon"),
}

_SNAP = {
    "unique_motif_count": 3.0,
    "choices_since_insight": 5.0,
    "fragment_buffer": ["hvad hvis jeg tog fejl ..."],
}


def _patch_gated_tick(stack: ExitStack) -> MagicMock:
    mod, fn = _GATED_TICK
    m = MagicMock(return_value={"generated": True, "insight": "jeg trækkes mod ro"})
    stack.enter_context(patch(f"{mod}.{fn}", m))
    return m


def _patch_nonllm_ticks(stack: ExitStack) -> dict[str, MagicMock]:
    mocks: dict[str, MagicMock] = {}
    for member, (mod, fn) in _NONLLM_TICKS.items():
        m = MagicMock(return_value={"generated": True, "member": member})
        stack.enter_context(patch(f"{mod}.{fn}", m))
        mocks[member] = m
    return mocks


# ---------------------------------------------------------------------------
# ONE gate for the whole family's LLM tier (the load-reduction invariant)
# ---------------------------------------------------------------------------


def test_aesthetic_family_gates_once():
    """The gated LLM tier consults should_generative_fire exactly ONCE."""
    fam = cdmf.build_aesthetic_family()
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


def test_build_aesthetic_family_declares_single_gated_member():
    fam = cdmf.build_aesthetic_family()
    assert fam.family_name == "cluster_aesthetic"
    assert {m.name for m in fam.members} == {"aesthetic_taste"}


def test_family_gate_receives_taste_namespaced_signals():
    fam = cdmf.build_aesthetic_family()
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

    assert seen["name"] == "cluster_aesthetic"
    assert any(k.startswith("aesthetic_taste:") for k in seen["signals"]), "gated member signals missing from the ONE gate"


# ---------------------------------------------------------------------------
# Dispatch — gated member runs iff the family gate fires
# ---------------------------------------------------------------------------


def test_fired_family_invokes_taste_member_with_skip_gate():
    fam = cdmf.build_aesthetic_family()
    with ExitStack() as stack:
        m = _patch_gated_tick(stack)
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=True))
        stack.enter_context(patch("core.services.central_core.central"))
        result = fam.tick(_SNAP, shadow=False)

    assert result["members_ran"] == ["aesthetic_taste"]
    assert m.call_count == 1
    # the family already gated → the daemon's own event-gate is bypassed
    assert m.call_args.kwargs.get("skip_event_gate") is True


def test_gate_skip_runs_no_taste_generation():
    fam = cdmf.build_aesthetic_family()
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
# Non-LLM member runs UNCONDITIONALLY (via the entry-point), gate or no gate
# ---------------------------------------------------------------------------


def test_curiosity_runs_when_gate_fires():
    with ExitStack() as stack:
        _patch_gated_tick(stack)
        nonllm = _patch_nonllm_ticks(stack)
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=True))
        stack.enter_context(patch("core.services.central_core.central"))
        stack.enter_context(patch.object(cdmf, "_collect_aesthetic_snapshot", return_value=_SNAP))
        result = cdmf.tick_cluster_aesthetic()

    assert nonllm["curiosity"].call_count == 1
    assert "curiosity" in result["members_ran"]
    # the fragment buffer is forwarded to the old daemon's tick
    assert nonllm["curiosity"].call_args.args[0] == _SNAP["fragment_buffer"]


def test_curiosity_runs_even_when_gate_does_not_fire():
    """The non-LLM curiosity scan must run every tick regardless of the
    generative family gate."""
    with ExitStack() as stack:
        gated = _patch_gated_tick(stack)
        nonllm = _patch_nonllm_ticks(stack)
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=False))
        stack.enter_context(patch("core.services.central_core.central"))
        stack.enter_context(patch.object(cdmf, "_collect_aesthetic_snapshot", return_value=_SNAP))
        result = cdmf.tick_cluster_aesthetic()

    # generative gate blocked the LLM member ...
    assert result["fired"] is False
    assert gated.call_count == 0
    # ... but the non-LLM curiosity member ran anyway
    assert nonllm["curiosity"].call_count == 1
    assert "curiosity" in result["members_ran"]


def test_both_members_run_in_one_tick():
    with ExitStack() as stack:
        gated = _patch_gated_tick(stack)
        nonllm = _patch_nonllm_ticks(stack)
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=True))
        stack.enter_context(patch("core.services.central_core.central"))
        stack.enter_context(patch.object(cdmf, "_collect_aesthetic_snapshot", return_value=_SNAP))
        result = cdmf.tick_cluster_aesthetic()

    assert set(result["members_ran"]) == {"aesthetic_taste", "curiosity"}
    assert gated.call_count == 1
    assert nonllm["curiosity"].call_count == 1


# ---------------------------------------------------------------------------
# Each member self-throttles on its OWN internal cadence
# ---------------------------------------------------------------------------


def test_curiosity_self_throttles_when_cadence_not_elapsed():
    """curiosity (5-min cadence) returns its throttled marker when its own cadence
    window hasn't elapsed — proving the family relies on the member's internal
    self-throttle (the family does NOT re-implement it)."""
    from datetime import UTC, datetime

    import core.services.curiosity_daemon as cud

    prev = cud._last_tick_at
    try:
        cud._last_tick_at = datetime.now(UTC)
        out = cdmf._aesthetic_curiosity_live({"fragment_buffer": ["hvorfor ...?"]})
        assert out == {"generated": False}
    finally:
        cud._last_tick_at = prev


def test_taste_member_self_throttles_via_time_gate():
    """aesthetic_taste keeps its motif-threshold + 30-min time-gate self-throttle
    even with skip_event_gate=True — the family only replaces the per-daemon
    event-gate, not the cadence guards."""
    from datetime import UTC, datetime

    import core.services.aesthetic_taste_daemon as atd

    prev_at = atd._last_insight_at
    prev_motifs = set(atd._accumulated_motifs)
    prev_seeded = atd._seeded
    try:
        atd._seeded = True  # skip DB seed
        atd._accumulated_motifs = {"a", "b", "c", "d"}  # above threshold
        atd._last_insight_at = datetime.now(UTC)  # inside the 30-min window
        out = cdmf._aesthetic_taste_live({})
        # time-gate short-circuits BEFORE any LLM generation
        assert out.get("generated") is False
    finally:
        atd._last_insight_at = prev_at
        atd._accumulated_motifs = prev_motifs
        atd._seeded = prev_seeded


# ---------------------------------------------------------------------------
# Load-bearing outputs preserved
# ---------------------------------------------------------------------------


def test_curiosity_output_recorded_in_family_result():
    """The curiosity member's output is echoed into the family result so the
    heartbeat/consumers still see it."""
    with ExitStack() as stack:
        _patch_gated_tick(stack)
        nonllm = _patch_nonllm_ticks(stack)
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=False))
        stack.enter_context(patch("core.services.central_core.central"))
        stack.enter_context(patch.object(cdmf, "_collect_aesthetic_snapshot", return_value=_SNAP))
        result = cdmf.tick_cluster_aesthetic()

    assert result["outputs"]["curiosity"] == {"generated": True, "member": "curiosity"}
    assert nonllm["curiosity"].call_count == 1


def test_snapshot_feeds_record_choice_load_bearing():
    """The family snapshot collector feeds record_choice every tick (replacing the
    retired heartbeat block), so build_taste_surface's choice log stays fresh."""
    with ExitStack() as stack:
        rec = MagicMock()
        stack.enter_context(patch("core.services.aesthetic_taste_daemon.record_choice", rec))
        stack.enter_context(patch("core.services.inner_voice_daemon.get_inner_voice_daemon_state", return_value={"last_result": {"mode": "reflective"}}))
        stack.enter_context(patch("core.runtime.db.recent_visible_runs", return_value=[{"text_preview": "jeg er her og det er godt"}]))
        stack.enter_context(patch("core.services.thought_stream_daemon.build_thought_stream_surface", return_value={"fragment_buffer": ["x"]}))
        snap = cdmf._collect_aesthetic_snapshot()

    rec.assert_called_once()
    assert rec.call_args.kwargs.get("mode") == "reflective"
    assert snap["fragment_buffer"] == ["x"]


# ---------------------------------------------------------------------------
# Self-safety
# ---------------------------------------------------------------------------


def test_curiosity_error_isolated_and_family_survives():
    with ExitStack() as stack:
        gated = _patch_gated_tick(stack)
        nonllm = _patch_nonllm_ticks(stack)
        nonllm["curiosity"].side_effect = RuntimeError("curiosity boom")
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=True))
        stack.enter_context(patch("core.services.central_core.central"))
        stack.enter_context(patch.object(cdmf, "_collect_aesthetic_snapshot", return_value=_SNAP))
        result = cdmf.tick_cluster_aesthetic()

    assert "curiosity" in result["member_errors"]
    assert "boom" in result["member_errors"]["curiosity"]
    # the gated member still ran despite the non-LLM member's error
    assert gated.call_count == 1
    assert "aesthetic_taste" in result["members_ran"]


def test_taste_error_does_not_crash_family():
    with ExitStack() as stack:
        m = _patch_gated_tick(stack)
        m.side_effect = RuntimeError("taste exploded")
        nonllm = _patch_nonllm_ticks(stack)
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=True))
        stack.enter_context(patch("core.services.central_core.central"))
        stack.enter_context(patch.object(cdmf, "_collect_aesthetic_snapshot", return_value=_SNAP))
        result = cdmf.tick_cluster_aesthetic()

    assert "aesthetic_taste" in result["member_errors"]
    assert "exploded" in result["member_errors"]["aesthetic_taste"]
    # the non-LLM curiosity sibling still ran despite the gated member's error
    assert nonllm["curiosity"].call_count == 1
    assert "curiosity" in result["members_ran"]


def test_entrypoint_never_raises_on_broken_family():
    with patch.object(cdmf, "aesthetic_family", side_effect=RuntimeError("family down")), \
         patch.object(cdmf, "_collect_aesthetic_snapshot", return_value=_SNAP):
        result = cdmf.tick_cluster_aesthetic()
    assert result["family"] == "cluster_aesthetic"
    assert result["gate_calls"] == 1
    assert "__entry__" in result["member_errors"]


def test_entrypoint_runs_live_by_default():
    """tick_cluster_aesthetic defaults to LIVE (shadow=False) so it produces."""
    with ExitStack() as stack:
        gated = _patch_gated_tick(stack)
        _patch_nonllm_ticks(stack)
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=True))
        stack.enter_context(patch("core.services.central_core.central"))
        stack.enter_context(patch.object(cdmf, "_collect_aesthetic_snapshot", return_value=_SNAP))
        result = cdmf.tick_cluster_aesthetic()

    assert result["shadow"] is False
    assert gated.call_count == 1


# ---------------------------------------------------------------------------
# Registration + retirement in daemon_manager
# ---------------------------------------------------------------------------


def test_cluster_aesthetic_registered_live():
    from core.services import daemon_manager as dm

    assert "cluster_aesthetic" in dm.get_daemon_names()
    states = {d["name"]: d for d in dm.get_all_daemon_states()}
    entry = states["cluster_aesthetic"]
    assert entry["enabled"] is True
    assert "aesthetic" in entry["description"]


def test_two_old_daemons_retired():
    from core.services import daemon_manager as dm

    retired = ["aesthetic_taste", "curiosity"]
    with patch.object(dm, "_load_state", return_value={}):
        for name in retired:
            assert dm._REGISTRY[name].get("default_enabled") is False, f"{name} must default disabled"
            assert dm._REGISTRY[name].get("retired") == "2026-07-15", f"{name} missing retired marker"
            assert "cluster_aesthetic" in dm._REGISTRY[name]["description"], f"{name} desc must point to cluster_aesthetic"
            assert dm.is_enabled(name) is False, f"{name} must be disabled (retired)"
