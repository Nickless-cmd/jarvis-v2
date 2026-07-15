"""E2E tests for the inner-voice cluster-daemon family #2 (spec 2026-07-14).

Consolidation contract:
* the family runs its event-gate ONCE for all 6 members (not 6 separate gates);
* when the gate fires, each member dispatches to the SAME generation function
  the old daemon used (output preserved);
* existential_wonder's ``_latest_wonder`` output — load-bearing for
  convene_judge / proactivity_bridge / visible_inner_life — still flows;
* the Lag-1 credit-assignment pass runs UNCONDITIONALLY every tick;
* a member error never crashes the family; the tick never raises;
* the 6 old daemons are RETIRED and cluster_innervoice is registered LIVE.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import core.services.cluster_daemon as cdm

# The 6 members and the (module, tick-fn) each dispatches to.
_MEMBER_TICKS = {
    "thought_stream": ("core.services.thought_stream_daemon", "tick_thought_stream_daemon"),
    "reflection_cycle": ("core.services.reflection_cycle_daemon", "tick_reflection_cycle_daemon"),
    "meta_reflection": ("core.services.meta_reflection_daemon", "tick_meta_reflection_daemon"),
    "irony": ("core.services.irony_daemon", "tick_irony_daemon"),
    "existential_wonder": ("core.services.existential_wonder_daemon", "tick_existential_wonder_daemon"),
    "creative_drift": ("core.services.creative_drift_daemon", "tick_creative_drift_daemon"),
}

_SNAP = {
    "energy_level": "medium",
    "inner_voice_mode": "rolig",
    "latest_fragment": "en tanke om kort dansk",
    "fragment_count": 5,
    "fragment_buffer": ["a", "b", "c"],
    "last_conflict": "splittet",
    "last_surprise": "uventet svar",
    "last_irony": "",
    "last_taste": "",
    "curiosity_signal": "",
    "absence_hours": 3.0,
    "user_inactive_min": 200.0,
    "cpu_pct": 20.0,
}


def _patch_member_ticks(stack: ExitStack) -> dict[str, MagicMock]:
    """Patch all 6 underlying daemon tick fns with mocks; return them by member."""
    mocks: dict[str, MagicMock] = {}
    for member, (mod, fn) in _MEMBER_TICKS.items():
        m = MagicMock(return_value={"generated": True, "member": member})
        stack.enter_context(patch(f"{mod}.{fn}", m))
        mocks[member] = m
    return mocks


# ---------------------------------------------------------------------------
# ONE gate for the whole family (the load-reduction invariant)
# ---------------------------------------------------------------------------


def test_innervoice_family_gates_once_not_six_times():
    """A 6-member family calls should_generative_fire exactly ONCE per tick."""
    fam = cdm.build_innervoice_family()
    calls = {"n": 0}

    def _fire(name, signals, **kw):
        calls["n"] += 1
        return True

    with ExitStack() as stack:
        _patch_member_ticks(stack)
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", side_effect=_fire))
        stack.enter_context(patch("core.services.central_core.central"))
        result = fam.tick(_SNAP, shadow=False)

    assert calls["n"] == 1, "family must gate ONCE, not once per member (6 old gates -> 1)"
    assert result["gate_calls"] == 1
    assert result["fired"] is True


def test_family_gate_receives_all_six_members_namespaced_signals():
    fam = cdm.build_innervoice_family()
    seen = {}

    def _fire(name, signals, **kw):
        seen["name"] = name
        seen["signals"] = dict(signals)
        return True

    with ExitStack() as stack:
        _patch_member_ticks(stack)
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", side_effect=_fire))
        stack.enter_context(patch("core.services.central_core.central"))
        fam.tick(_SNAP, shadow=False)

    assert seen["name"] == "cluster_innervoice"
    # every member contributed at least one namespaced signal
    for member in _MEMBER_TICKS:
        assert any(k.startswith(f"{member}:") for k in seen["signals"]), f"{member} signals missing from the ONE gate"


# ---------------------------------------------------------------------------
# Dispatch — each member's real generation path is invoked when the gate fires
# ---------------------------------------------------------------------------


def test_fired_family_invokes_every_member_generation_with_skip_gate():
    fam = cdm.build_innervoice_family()
    with ExitStack() as stack:
        mocks = _patch_member_ticks(stack)
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=True))
        stack.enter_context(patch("core.services.central_core.central"))
        result = fam.tick(_SNAP, shadow=False)

    assert set(result["members_ran"]) == set(_MEMBER_TICKS.keys())
    for member, m in mocks.items():
        assert m.call_count == 1, f"{member} generation not invoked"
    # members that reuse a shared gate must skip their own redundant event-gate
    for member in ("thought_stream", "reflection_cycle", "meta_reflection", "irony",
                   "existential_wonder", "creative_drift"):
        _, kwargs = mocks[member].call_args
        assert kwargs.get("skip_event_gate") is True, f"{member} must skip its own gate (family owns it)"
    # meta additionally skips its own credit pass (cluster runs it unconditionally)
    assert mocks["meta_reflection"].call_args.kwargs.get("skip_credit") is True


def test_gate_skip_runs_no_member_generation():
    fam = cdm.build_innervoice_family()
    with ExitStack() as stack:
        mocks = _patch_member_ticks(stack)
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=False))
        stack.enter_context(patch("core.services.central_core.central"))
        result = fam.tick(_SNAP, shadow=False)

    assert result["fired"] is False
    assert result["members_ran"] == []
    assert result["gate_calls"] == 1
    for m in mocks.values():
        assert m.call_count == 0


# ---------------------------------------------------------------------------
# existential_wonder output is load-bearing — it MUST keep flowing
# ---------------------------------------------------------------------------


def test_existential_wonder_output_still_produced_by_cluster():
    """When the family fires, the wonder member fills _latest_wonder that
    convene_judge / proactivity_bridge / visible_inner_life read."""
    import core.services.existential_wonder_daemon as ew

    fixed = "Er en foldet tanke stadig min egen?"
    with ExitStack() as stack:
        # real wonder tick, but stub the LLM + persistence + convene side-effects
        stack.enter_context(patch.object(ew, "_generate_wonder_question", return_value=fixed))
        stack.enter_context(patch.object(ew, "_store_wonder"))
        stack.enter_context(patch.object(ew, "_maybe_propose_convening", return_value=False))
        # patch the OTHER five members so only wonder does real work
        for member, (mod, fn) in _MEMBER_TICKS.items():
            if member == "existential_wonder":
                continue
            stack.enter_context(patch(f"{mod}.{fn}", MagicMock(return_value={"generated": False})))
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=True))
        stack.enter_context(patch("core.services.central_core.central"))

        # reset wonder rate-limit floor so it generates this tick
        ew._last_tick_at = None
        ew._latest_wonder = ""

        cdm.build_innervoice_family().tick(_SNAP, shadow=False)

    # the load-bearing output flowed
    assert ew.get_latest_wonder() == fixed
    assert ew.build_existential_wonder_surface()["latest_wonder"] == fixed


def test_wonder_preconditions_still_gate_output():
    """Wonder must NOT fire when the quiet-period preconditions are unmet
    (short absence), even if the family gate fired."""
    import core.services.existential_wonder_daemon as ew

    with ExitStack() as stack:
        gen = patch.object(ew, "_generate_wonder_question", return_value="x?")
        stack.enter_context(gen)
        stack.enter_context(patch.object(ew, "_store_wonder"))
        for member, (mod, fn) in _MEMBER_TICKS.items():
            if member == "existential_wonder":
                continue
            stack.enter_context(patch(f"{mod}.{fn}", MagicMock(return_value={"generated": False})))
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=True))
        stack.enter_context(patch("core.services.central_core.central"))

        ew._last_tick_at = None
        ew._latest_wonder = "prior"
        short_absence = dict(_SNAP, absence_hours=0.1)  # below _MIN_ABSENCE_HOURS
        cdm.build_innervoice_family().tick(short_absence, shadow=False)

    # precondition blocked generation; prior output NOT cleared (never silence)
    assert ew.get_latest_wonder() == "prior"


# ---------------------------------------------------------------------------
# Credit assignment runs unconditionally every tick (via the entry-point)
# ---------------------------------------------------------------------------


def test_credit_assignment_runs_even_when_gate_does_not_fire():
    with ExitStack() as stack:
        _patch_member_ticks(stack)
        credit = MagicMock(return_value={"checked": True})
        stack.enter_context(patch("core.services.meta_reflection_daemon.run_credit_assignment", credit))
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=False))
        stack.enter_context(patch("core.services.central_core.central"))
        stack.enter_context(patch.object(cdm, "_collect_innervoice_snapshot", return_value=_SNAP))
        cdm.tick_cluster_innervoice()

    assert credit.call_count == 1, "credit assignment must run every tick, independent of the family gate"


# ---------------------------------------------------------------------------
# Self-safety
# ---------------------------------------------------------------------------


def test_member_error_does_not_crash_family():
    fam = cdm.build_innervoice_family()
    with ExitStack() as stack:
        mocks = _patch_member_ticks(stack)
        mocks["irony"].side_effect = RuntimeError("irony exploded")
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=True))
        stack.enter_context(patch("core.services.central_core.central"))
        result = fam.tick(_SNAP, shadow=False)

    assert "irony" in result["member_errors"]
    assert "exploded" in result["member_errors"]["irony"]
    # every sibling still ran
    assert set(result["members_ran"]) == set(_MEMBER_TICKS) - {"irony"}


def test_entrypoint_never_raises_on_broken_family():
    with patch.object(cdm, "innervoice_family", side_effect=RuntimeError("family down")), \
         patch.object(cdm, "_collect_innervoice_snapshot", return_value=_SNAP), \
         patch("core.services.meta_reflection_daemon.run_credit_assignment"):
        result = cdm.tick_cluster_innervoice()
    assert result["family"] == "cluster_innervoice"
    assert result["gate_calls"] == 1
    assert "__entry__" in result["member_errors"]


def test_entrypoint_runs_live_by_default():
    """tick_cluster_innervoice defaults to LIVE (shadow=False) so it produces,
    not merely observes."""
    with ExitStack() as stack:
        mocks = _patch_member_ticks(stack)
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", return_value=True))
        stack.enter_context(patch("core.services.central_core.central"))
        stack.enter_context(patch.object(cdm, "_collect_innervoice_snapshot", return_value=_SNAP))
        stack.enter_context(patch("core.services.meta_reflection_daemon.run_credit_assignment"))
        result = cdm.tick_cluster_innervoice()

    assert result["shadow"] is False
    # live path went through each member's real generation fn (not observe)
    for member, m in mocks.items():
        assert m.call_count == 1, f"{member} live generation not invoked"


# ---------------------------------------------------------------------------
# Registration + retirement in daemon_manager
# ---------------------------------------------------------------------------


def test_cluster_innervoice_registered_live():
    from core.services import daemon_manager as dm

    assert "cluster_innervoice" in dm.get_daemon_names()
    states = {d["name"]: d for d in dm.get_all_daemon_states()}
    entry = states["cluster_innervoice"]
    assert entry["enabled"] is True
    assert "inner-voice" in entry["description"]


def test_six_old_innervoice_daemons_retired():
    from core.services import daemon_manager as dm

    retired = ["thought_stream", "reflection_cycle", "meta_reflection",
               "irony", "existential_wonder", "creative_drift"]
    # isolate from any persisted DAEMON_STATE.json so we test the defaults
    with patch.object(dm, "_load_state", return_value={}):
        for name in retired:
            assert dm._REGISTRY[name].get("default_enabled") is False, f"{name} must default disabled"
            assert dm._REGISTRY[name].get("retired") == "2026-07-15", f"{name} missing retired marker"
            assert dm.is_enabled(name) is False, f"{name} must be disabled (retired)"
