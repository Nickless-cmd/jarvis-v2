"""E2E tests for the affect cluster-daemon family #3 (spec 2026-07-14).

Consolidation contract:
* the family runs its event-gate ONCE for all THREE gated LLM members
  (surprise + conflict + desire), not 3 separate gates;
* when the gate fires, each gated member dispatches to the SAME generation
  function the old daemon used, with ``skip_event_gate=True`` (output preserved
  via the same caches every consumer reads);
* surprise/conflict caches are load-bearing for cluster_innervoice — they must
  keep filling;
* the TWO non-LLM members (longing_signal, emotion_repair_bridge) run
  UNCONDITIONALLY every tick, independent of the family generative gate;
* a member error never crashes the family; the tick never raises;
* the 5 old affect daemons are RETIRED and cluster_affect is registered LIVE.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import core.services.cluster_daemon as cdm

# The 3 GATED LLM members and the (module, tick-fn) each dispatches to.
_GATED_TICKS = {
    "surprise": ("core.services.surprise_daemon", "tick_surprise_daemon"),
    "conflict": ("core.services.conflict_daemon", "tick_conflict_daemon"),
    "desire": ("core.services.desire_daemon", "tick_desire_daemon"),
}

# The 2 NON-LLM members and the (module, tick-fn) each runs unconditionally.
_NONLLM_TICKS = {
    "longing_signal": ("core.services.longing_signal_daemon", "run_longing_signal_daemon_tick"),
    "emotion_repair_bridge": ("core.services.emotion_repair_bridge_daemon", "tick_emotion_repair_bridge"),
}

_SNAP = {
    "inner_voice_mode": "rolig",
    "somatic_energy": "medium",
    "conflict_snapshot": {
        "energy_level": "medium",
        "inner_voice_mode": "rolig",
        "pending_proposals_count": 2,
        "latest_fragment": "en tanke",
        "last_surprise": "uventet svar",
        "last_surprise_at": "",
        "fragment_count": 5,
    },
    "desire_signals": {"curiosity": "hvorfor", "craft": "byg", "connection": "bjorn"},
}


def _patch_gated_ticks(stack: ExitStack) -> dict[str, MagicMock]:
    mocks: dict[str, MagicMock] = {}
    for member, (mod, fn) in _GATED_TICKS.items():
        m = MagicMock(return_value={"generated": True, "member": member})
        stack.enter_context(patch(f"{mod}.{fn}", m))
        mocks[member] = m
    return mocks


def _patch_nonllm_ticks(stack: ExitStack) -> dict[str, MagicMock]:
    mocks: dict[str, MagicMock] = {}
    for member, (mod, fn) in _NONLLM_TICKS.items():
        m = MagicMock(return_value={"status": "ok", "member": member})
        stack.enter_context(patch(f"{mod}.{fn}", m))
        mocks[member] = m
    return mocks


# ---------------------------------------------------------------------------
# ONE gate for the whole family (the load-reduction invariant)
# ---------------------------------------------------------------------------


def test_affect_family_gates_once_not_thrice():
    """A 3-gated-member family calls should_generative_fire exactly ONCE."""
    fam = cdm.build_affect_family()
    calls = {"n": 0}

    def _fire(name, signals, **kw):
        calls["n"] += 1
        return True

    with ExitStack() as stack:
        _patch_gated_ticks(stack)
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", side_effect=_fire))
        stack.enter_context(patch("core.services.central_core.central"))
        result = fam.tick(_SNAP, shadow=False)

    assert calls["n"] == 1, "family must gate ONCE, not once per member (3 old gates -> 1)"
    assert result["gate_calls"] == 1
    assert result["fired"] is True


def test_family_gate_receives_all_three_members_namespaced_signals():
    fam = cdm.build_affect_family()
    seen = {}

    def _fire(name, signals, **kw):
        seen["name"] = name
        seen["signals"] = dict(signals)
        return True

    with ExitStack() as stack:
        _patch_gated_ticks(stack)
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", side_effect=_fire))
        stack.enter_context(patch("core.services.central_core.central"))
        fam.tick(_SNAP, shadow=False)

    assert seen["name"] == "cluster_affect"
    for member in _GATED_TICKS:
        assert any(k.startswith(f"{member}:") for k in seen["signals"]), f"{member} signals missing from the ONE gate"


# ---------------------------------------------------------------------------
# Dispatch — each gated member's real generation path is invoked, skip_event_gate
# ---------------------------------------------------------------------------


def test_fired_family_invokes_gated_members_with_skip_gate():
    fam = cdm.build_affect_family()
    with ExitStack() as stack:
        mocks = _patch_gated_ticks(stack)
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=True))
        stack.enter_context(patch("core.services.central_core.central"))
        result = fam.tick(_SNAP, shadow=False)

    assert set(result["members_ran"]) == set(_GATED_TICKS.keys())
    for member, m in mocks.items():
        assert m.call_count == 1, f"{member} generation not invoked"
        assert m.call_args.kwargs.get("skip_event_gate") is True, f"{member} must skip its own gate (family owns it)"


def test_gate_skip_runs_no_gated_generation():
    fam = cdm.build_affect_family()
    with ExitStack() as stack:
        mocks = _patch_gated_ticks(stack)
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=False))
        stack.enter_context(patch("core.services.central_core.central"))
        result = fam.tick(_SNAP, shadow=False)

    assert result["fired"] is False
    assert result["members_ran"] == []
    for m in mocks.values():
        assert m.call_count == 0


# ---------------------------------------------------------------------------
# Non-LLM members run UNCONDITIONALLY (via the entry-point), gate or no gate
# ---------------------------------------------------------------------------


def test_nonllm_members_run_when_gate_fires():
    with ExitStack() as stack:
        _patch_gated_ticks(stack)
        nonllm = _patch_nonllm_ticks(stack)
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=True))
        stack.enter_context(patch("core.services.central_core.central"))
        stack.enter_context(patch.object(cdm, "_collect_affect_snapshot", return_value=_SNAP))
        result = cdm.tick_cluster_affect()

    for member, m in nonllm.items():
        assert m.call_count == 1, f"{member} must run"
        assert member in result["members_ran"]


def test_nonllm_members_run_even_when_gate_does_not_fire():
    """The load-bearing rules — longing ingest + emotion→repair — must run every
    tick regardless of whether the generative family gate fired."""
    with ExitStack() as stack:
        gated = _patch_gated_ticks(stack)
        nonllm = _patch_nonllm_ticks(stack)
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=False))
        stack.enter_context(patch("core.services.central_core.central"))
        stack.enter_context(patch.object(cdm, "_collect_affect_snapshot", return_value=_SNAP))
        result = cdm.tick_cluster_affect()

    # generative gate blocked the 3 LLM members ...
    assert result["fired"] is False
    for m in gated.values():
        assert m.call_count == 0
    # ... but the 2 non-LLM members ran anyway
    for member, m in nonllm.items():
        assert m.call_count == 1, f"{member} must run unconditionally"
        assert member in result["members_ran"]


# ---------------------------------------------------------------------------
# surprise / conflict caches are load-bearing for cluster_innervoice
# ---------------------------------------------------------------------------


def test_surprise_and_conflict_caches_flow_through_cluster():
    """When the family fires, surprise + conflict members fill the module caches
    that cluster_innervoice (and reflection) read via get_latest_*/build_*."""
    import core.services.surprise_daemon as sd
    import core.services.conflict_daemon as cd

    with ExitStack() as stack:
        # real surprise/conflict ticks, but stub LLM + persistence side-effects
        stack.enter_context(patch.object(sd, "_generate_surprise", return_value="alt vippede"))
        stack.enter_context(patch.object(sd, "_store_surprise", side_effect=lambda phrase, div: setattr(sd, "_cached_surprise", phrase)))
        stack.enter_context(patch.object(cd, "_detect_conflict", return_value="drive-vs-rest"))
        stack.enter_context(patch.object(cd, "_generate_conflict_phrase", return_value="jeg er splittet"))
        stack.enter_context(patch.object(cd, "_store_conflict", side_effect=lambda phrase, ct: setattr(cd, "_cached_conflict", phrase)))
        # stub the surprise history/cooldown guards so it generates this tick
        stack.enter_context(patch.object(sd, "_compute_divergence", return_value=["mode:a->b"]))
        stack.enter_context(patch("core.services.desire_daemon.tick_desire_daemon", MagicMock(return_value={})))
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=True))
        stack.enter_context(patch("core.services.central_core.central"))

        sd._cached_surprise = ""
        sd._heartbeats_since_surprise = 999
        sd._mode_history = ["a", "b", "c"]
        cd._cached_conflict = ""
        cd._cached_conflict_at = None

        cdm.build_affect_family().tick(_SNAP, shadow=False)

    assert sd.get_latest_surprise() == "alt vippede"
    assert cd.get_latest_conflict() == "jeg er splittet"


# ---------------------------------------------------------------------------
# Self-safety
# ---------------------------------------------------------------------------


def test_gated_member_error_does_not_crash_family():
    fam = cdm.build_affect_family()
    with ExitStack() as stack:
        mocks = _patch_gated_ticks(stack)
        mocks["conflict"].side_effect = RuntimeError("conflict exploded")
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=True))
        stack.enter_context(patch("core.services.central_core.central"))
        result = fam.tick(_SNAP, shadow=False)

    assert "conflict" in result["member_errors"]
    assert "exploded" in result["member_errors"]["conflict"]
    assert set(result["members_ran"]) == set(_GATED_TICKS) - {"conflict"}


def test_nonllm_member_error_isolated_and_siblings_still_run():
    with ExitStack() as stack:
        _patch_gated_ticks(stack)
        nonllm = _patch_nonllm_ticks(stack)
        nonllm["longing_signal"].side_effect = RuntimeError("longing boom")
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=True))
        stack.enter_context(patch("core.services.central_core.central"))
        stack.enter_context(patch.object(cdm, "_collect_affect_snapshot", return_value=_SNAP))
        result = cdm.tick_cluster_affect()

    assert "longing_signal" in result["member_errors"]
    assert "boom" in result["member_errors"]["longing_signal"]
    # sibling non-LLM member still ran despite the other's error
    assert nonllm["emotion_repair_bridge"].call_count == 1
    assert "emotion_repair_bridge" in result["members_ran"]


def test_entrypoint_never_raises_on_broken_family():
    with patch.object(cdm, "affect_family", side_effect=RuntimeError("family down")), \
         patch.object(cdm, "_collect_affect_snapshot", return_value=_SNAP):
        result = cdm.tick_cluster_affect()
    assert result["family"] == "cluster_affect"
    assert result["gate_calls"] == 1
    assert "__entry__" in result["member_errors"]


def test_entrypoint_runs_live_by_default():
    """tick_cluster_affect defaults to LIVE (shadow=False) so it produces."""
    with ExitStack() as stack:
        mocks = _patch_gated_ticks(stack)
        _patch_nonllm_ticks(stack)
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=True))
        stack.enter_context(patch("core.services.central_core.central"))
        stack.enter_context(patch.object(cdm, "_collect_affect_snapshot", return_value=_SNAP))
        result = cdm.tick_cluster_affect()

    assert result["shadow"] is False
    for member, m in mocks.items():
        assert m.call_count == 1, f"{member} live generation not invoked"


# ---------------------------------------------------------------------------
# Registration + retirement in daemon_manager
# ---------------------------------------------------------------------------


def test_cluster_affect_registered_live():
    from core.services import daemon_manager as dm

    assert "cluster_affect" in dm.get_daemon_names()
    states = {d["name"]: d for d in dm.get_all_daemon_states()}
    entry = states["cluster_affect"]
    assert entry["enabled"] is True
    assert "affect" in entry["description"]


def test_five_old_affect_daemons_retired():
    from core.services import daemon_manager as dm

    retired = ["surprise", "conflict", "desire", "longing_signal", "emotion_repair_bridge"]
    with patch.object(dm, "_load_state", return_value={}):
        for name in retired:
            assert dm._REGISTRY[name].get("default_enabled") is False, f"{name} must default disabled"
            assert dm._REGISTRY[name].get("retired") == "2026-07-15", f"{name} missing retired marker"
            assert dm.is_enabled(name) is False, f"{name} must be disabled (retired)"
