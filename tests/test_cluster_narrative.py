"""E2E tests for the narrative cluster-daemon family #4 (spec 2026-07-14).

Consolidation contract:
* the family folds 5 TIME-BASED self-narrative/identity daemons into ONE tick +
  ONE registry entry — it is NOT event-gated (no should_generative_fire call);
* every member runs UNCONDITIONALLY each family tick and dispatches to the old
  daemon's self-throttling ``tick_*`` (no args), so each keeps its OWN cadence
  (24h / 15min / 24h / 6h / 24h) and never double-fires within its window;
* the development-narrative log and the identity_drift snapshot are load-bearing
  and must keep flowing to their consumers;
* a member error never crashes the family; the tick never raises;
* the 5 old daemons are RETIRED and cluster_narrative is registered LIVE.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contextlib import ExitStack
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import core.services.cluster_daemon as cdm

# The 5 members and the (module, tick-fn) each dispatches to.
_MEMBER_TICKS = {
    "development_narrative": ("core.services.development_narrative_daemon", "tick_development_narrative_daemon"),
    "narrative_summary": ("core.services.narrative_summary_daemon", "tick_narrative_summary_daemon"),
    "identity_drift": ("core.services.identity_drift_daemon", "tick_identity_drift_daemon"),
    "identity_sketch": ("core.services.identity_sketch", "tick_identity_sketch_daemon"),
    "consolidation_judge": ("core.services.consolidation_judge_daemon", "tick_consolidation_judge_daemon"),
}


def _patch_member_ticks(stack: ExitStack) -> dict[str, MagicMock]:
    mocks: dict[str, MagicMock] = {}
    for member, (mod, fn) in _MEMBER_TICKS.items():
        m = MagicMock(return_value={"ran": True, "member": member})
        stack.enter_context(patch(f"{mod}.{fn}", m))
        mocks[member] = m
    return mocks


# ---------------------------------------------------------------------------
# ONE family tick runs all 5 members (the consolidation invariant)
# ---------------------------------------------------------------------------


def test_family_runs_all_five_members():
    with ExitStack() as stack:
        mocks = _patch_member_ticks(stack)
        stack.enter_context(patch("core.services.central_core.central"))
        result = cdm.tick_cluster_narrative()

    assert result["family"] == "cluster_narrative"
    assert result["shadow"] is False
    assert result["fired"] is True
    assert set(result["members_ran"]) == set(_MEMBER_TICKS.keys())
    for member, m in mocks.items():
        assert m.call_count == 1, f"{member} not invoked by the family tick"
    # every member's output is surfaced (parity with the old daemons' outputs)
    for member in _MEMBER_TICKS:
        assert member in result["outputs"]


def test_build_narrative_family_declares_five_members():
    fam = cdm.build_narrative_family()
    assert fam.family_name == "cluster_narrative"
    names = {m.name for m in fam.members}
    assert names == set(_MEMBER_TICKS.keys())


# ---------------------------------------------------------------------------
# TIME-BASED — no should_generative_fire event-gate (KEY DIFFERENCE from #2/#3)
# ---------------------------------------------------------------------------


def test_family_never_consults_event_gate():
    """This family is time-based; folding it in must NOT add an event-gate.
    should_generative_fire must never be called even when event-driven mode is on."""
    with ExitStack() as stack:
        _patch_member_ticks(stack)
        stack.enter_context(patch("core.services.central_core.central"))
        stack.enter_context(patch("core.services.event_gate.event_driven_enabled", return_value=True))
        fire = MagicMock(return_value=True)
        stack.enter_context(patch("core.services.event_gate.should_generative_fire", side_effect=fire))
        result = cdm.tick_cluster_narrative()

    assert fire.call_count == 0, "narrative family must not use the generative event-gate"
    assert result["gate_calls"] == 0


# ---------------------------------------------------------------------------
# Each member self-throttles on its OWN cadence (doesn't fire twice/day)
# ---------------------------------------------------------------------------


def test_datetime_members_self_throttle_when_cadence_not_elapsed():
    """The 4 datetime-gated members return their throttled marker (no second
    fire) when their own cadence window has not elapsed."""
    import core.services.development_narrative_daemon as dnd
    import core.services.identity_drift_daemon as idd
    import core.services.consolidation_judge_daemon as cjd
    import core.services.narrative_summary_daemon as nsd

    now = datetime.now(UTC)
    dnd._last_narrative_at = now
    idd._last_tick_at = now
    cjd._last_judgment_at = now
    nsd._last_tick_at = now

    assert dnd.tick_development_narrative_daemon() == {"generated": False}
    assert idd.tick_identity_drift_daemon() == {"checked": False}
    cj = cjd.tick_consolidation_judge_daemon()
    assert cj["generated"] is False and cj["reason"] == "cadence_not_reached"
    ns = nsd.tick_narrative_summary_daemon()
    assert ns["ran"] is False and ns["reason"] == "cadence-not-elapsed"


def test_identity_sketch_member_self_throttles_when_fresh():
    """identity_sketch skips regeneration while its state is still fresh (<6h)."""
    import core.services.identity_sketch as isk

    fresh = {"version": 3, "updated_at": datetime.now(UTC).isoformat(), "content": "hej"}
    with patch.object(isk, "get_identity_sketch", return_value=fresh):
        result = isk.tick_identity_sketch_daemon()
    assert result["action"] == "skipped"
    assert result["reason"] == "fresh"


# ---------------------------------------------------------------------------
# Load-bearing outputs preserved
# ---------------------------------------------------------------------------


def test_development_narrative_cache_flows_through_cluster():
    """When the family runs, the development_narrative member fills the module
    cache that the heartbeat influence trace reads via get_latest_*."""
    import core.services.development_narrative_daemon as dnd

    with ExitStack() as stack:
        stack.enter_context(patch("core.services.central_core.central"))
        stack.enter_context(patch.object(dnd, "_generate_narrative", return_value="jeg er blevet mere rolig"))
        stack.enter_context(patch.object(dnd, "insert_private_brain_record"))
        stack.enter_context(patch.object(dnd, "event_bus"))
        # stub the other 4 members so the test isolates development_narrative
        for member, (mod, fn) in _MEMBER_TICKS.items():
            if member == "development_narrative":
                continue
            stack.enter_context(patch(f"{mod}.{fn}", MagicMock(return_value={})))
        dnd._last_narrative_at = None
        dnd._cached_narrative = ""
        cdm.tick_cluster_narrative()

    assert dnd.get_latest_development_narrative() == "jeg er blevet mere rolig"


def test_identity_drift_gets_a_live_tick_via_the_family():
    """identity_drift was orphaned (registered, never ticked); the family gives
    it a live tick site so its snapshot consumers keep getting data."""
    with ExitStack() as stack:
        mocks = _patch_member_ticks(stack)
        stack.enter_context(patch("core.services.central_core.central"))
        result = cdm.tick_cluster_narrative()

    assert mocks["identity_drift"].call_count == 1
    assert "identity_drift" in result["members_ran"]


# ---------------------------------------------------------------------------
# Self-safety
# ---------------------------------------------------------------------------


def test_member_error_isolated_and_siblings_still_run():
    with ExitStack() as stack:
        mocks = _patch_member_ticks(stack)
        mocks["consolidation_judge"].side_effect = RuntimeError("judge exploded")
        stack.enter_context(patch("core.services.central_core.central"))
        result = cdm.tick_cluster_narrative()

    assert "consolidation_judge" in result["member_errors"]
    assert "exploded" in result["member_errors"]["consolidation_judge"]
    # every sibling still ran despite the error
    assert set(result["members_ran"]) == set(_MEMBER_TICKS) - {"consolidation_judge"}


def test_entrypoint_never_raises_on_broken_family():
    with patch.object(cdm, "narrative_family", side_effect=RuntimeError("family down")):
        result = cdm.tick_cluster_narrative()
    assert result["family"] == "cluster_narrative"
    assert result["gate_calls"] == 0
    assert "__entry__" in result["member_errors"]


# ---------------------------------------------------------------------------
# Registration + retirement in daemon_manager
# ---------------------------------------------------------------------------


def test_cluster_narrative_registered_live():
    from core.services import daemon_manager as dm

    assert "cluster_narrative" in dm.get_daemon_names()
    states = {d["name"]: d for d in dm.get_all_daemon_states()}
    entry = states["cluster_narrative"]
    assert entry["enabled"] is True
    assert "narrative" in entry["description"]
    # DAILY-appropriate cadence marker (dominant self-narrative rhythm)
    assert dm._REGISTRY["cluster_narrative"]["default_cadence_minutes"] == 1440


def test_five_old_narrative_daemons_retired():
    from core.services import daemon_manager as dm

    retired = [
        "development_narrative", "narrative_summary", "identity_drift",
        "identity_sketch", "consolidation_judge",
    ]
    with patch.object(dm, "_load_state", return_value={}):
        for name in retired:
            assert dm._REGISTRY[name].get("default_enabled") is False, f"{name} must default disabled"
            assert dm._REGISTRY[name].get("retired") == "2026-07-15", f"{name} missing retired marker"
            assert "cluster_narrative" in dm._REGISTRY[name]["description"], f"{name} desc must point to cluster_narrative"
            assert dm.is_enabled(name) is False, f"{name} must be disabled (retired)"
