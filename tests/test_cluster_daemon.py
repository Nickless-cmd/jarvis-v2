"""Tests for the cluster-daemon primitive (spec 2026-07-14).

Verifies the load-reduction + safety invariants of :mod:`core.services.cluster_daemon`:
* the family runs its event-gate ONCE (not N times, one per member);
* a fired family dispatches to its members;
* a member error does NOT crash the family (self-safe);
* the somatic family runs LIVE by default — it PRODUCES the 3 members' outputs
  (calls the old ``tick_*`` daemons) rather than merely observing, the 3 old
  daemons (somatic / experienced_time / absence) are retired, member errors are
  isolated, and the entry-point never raises;
* the observe-only SHADOW path is still reachable via ``tick(shadow=True)`` and
  reports parity telemetry to Central under a ``cluster_shadow`` marker.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unittest.mock import patch

import core.services.cluster_daemon as cdm
from core.services.cluster_daemon import ClusterDaemon, ClusterMember


def _member(name: str, *, boom: bool = False) -> ClusterMember:
    def _observe(snap: dict):
        if boom:
            raise RuntimeError(f"{name} exploded")
        return {"name": name, "seen": dict(snap)}

    return ClusterMember(
        name=name,
        signals=lambda snap: {"v": float(snap.get(name, 0.0))},
        observe=_observe,
    )


def _family(members) -> ClusterDaemon:
    return ClusterDaemon(family_name="cluster_test", members=members)


# ---------------------------------------------------------------------------
# ONE gate for the whole family (the load-reduction invariant)
# ---------------------------------------------------------------------------


def test_family_gates_once_not_per_member():
    """A 3-member family calls should_generative_fire exactly ONCE per tick."""
    fam = _family([_member("a"), _member("b"), _member("c")])
    calls = {"n": 0}

    def _fake_fire(name, signals, **kw):
        calls["n"] += 1
        return True

    with patch("core.services.event_gate.event_driven_enabled", return_value=True), \
         patch("core.services.event_gate.should_generative_fire", side_effect=_fake_fire):
        result = fam.tick({"a": 0.2, "b": 0.4, "c": 0.6}, shadow=True)

    assert calls["n"] == 1, "family must gate ONCE, not once per member"
    assert result["gate_calls"] == 1
    assert result["fired"] is True


def test_family_gate_receives_aggregated_namespaced_signals():
    """The single gate call gets every member's signals namespaced member:signal."""
    fam = _family([_member("a"), _member("b")])
    seen = {}

    def _fake_fire(name, signals, **kw):
        seen["name"] = name
        seen["signals"] = dict(signals)
        return True

    with patch("core.services.event_gate.event_driven_enabled", return_value=True), \
         patch("core.services.event_gate.should_generative_fire", side_effect=_fake_fire):
        fam.tick({"a": 0.1, "b": 0.9}, shadow=True)

    assert seen["name"] == "cluster_test"
    assert seen["signals"] == {"a:v": 0.1, "b:v": 0.9}


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


def test_fired_family_dispatches_to_all_members():
    fam = _family([_member("a"), _member("b"), _member("c")])
    with patch("core.services.event_gate.event_driven_enabled", return_value=True), \
         patch("core.services.event_gate.should_generative_fire", return_value=True):
        result = fam.tick({"a": 1, "b": 1, "c": 1}, shadow=True)

    assert set(result["members_ran"]) == {"a", "b", "c"}
    assert set(result["outputs"].keys()) == {"a", "b", "c"}
    assert not result["member_errors"]


def test_gate_skip_runs_no_members():
    """When the family gate does not fire, NO member runs (the load reduction)."""
    fam = _family([_member("a"), _member("b")])
    with patch("core.services.event_gate.event_driven_enabled", return_value=True), \
         patch("core.services.event_gate.should_generative_fire", return_value=False):
        result = fam.tick({"a": 0, "b": 0}, shadow=True)

    assert result["fired"] is False
    assert result["members_ran"] == []
    assert result["outputs"] == {}
    assert result["gate_calls"] == 1


def test_relevance_predicate_skips_irrelevant_member():
    m_a = _member("a")
    m_b = ClusterMember(
        name="b",
        signals=lambda snap: {"v": 0.0},
        observe=lambda snap: {"name": "b"},
        relevant=lambda snap: False,
    )
    fam = _family([m_a, m_b])
    with patch("core.services.event_gate.event_driven_enabled", return_value=True), \
         patch("core.services.event_gate.should_generative_fire", return_value=True):
        result = fam.tick({"a": 1}, shadow=True)

    assert result["members_ran"] == ["a"]
    assert result["members_skipped"] == ["b"]


# ---------------------------------------------------------------------------
# Self-safety
# ---------------------------------------------------------------------------


def test_member_error_does_not_crash_family():
    """A member that raises is captured; sibling members still run."""
    fam = _family([_member("a"), _member("b", boom=True), _member("c")])
    with patch("core.services.event_gate.event_driven_enabled", return_value=True), \
         patch("core.services.event_gate.should_generative_fire", return_value=True):
        result = fam.tick({"a": 1, "b": 1, "c": 1}, shadow=True)

    assert set(result["members_ran"]) == {"a", "c"}
    assert "b" in result["member_errors"]
    assert "exploded" in result["member_errors"]["b"]


def test_broken_gate_fails_open_to_fire():
    """If the gate blows up, the family FIRES (never silences Jarvis)."""
    fam = _family([_member("a")])
    with patch("core.services.event_gate.event_driven_enabled", return_value=True), \
         patch("core.services.event_gate.should_generative_fire", side_effect=RuntimeError("gate down")):
        result = fam.tick({"a": 1}, shadow=True)

    assert result["fired"] is True
    assert result["members_ran"] == ["a"]


def test_tick_never_raises_on_broken_snapshot_collector():
    def _boom():
        raise RuntimeError("collector down")

    fam = ClusterDaemon(family_name="cluster_test", members=[_member("a")], collect_snapshot=_boom)
    with patch("core.services.event_gate.event_driven_enabled", return_value=False):
        # zero-arg tick → uses the (broken) collector; must degrade, not raise
        result = fam.tick(shadow=True)
    assert result["family"] == "cluster_test"
    assert result["gate_calls"] == 1


# ---------------------------------------------------------------------------
# Shadow / parity — does NOT disable the old daemons
# ---------------------------------------------------------------------------


def test_shadow_reports_to_central_with_cluster_shadow_marker():
    fam = _family([_member("a"), _member("b")])
    captured = {}

    class _FakeCentral:
        def observe(self, event, **kw):
            captured.update(event)

    with patch("core.services.event_gate.event_driven_enabled", return_value=True), \
         patch("core.services.event_gate.should_generative_fire", return_value=True), \
         patch("core.services.central_core.central", return_value=_FakeCentral()):
        fam.tick({"a": 1, "b": 1}, shadow=True)

    assert captured.get("cluster_shadow") is True
    assert captured.get("nerve") == "cluster_test"
    assert captured.get("kind") == "cluster_tick"
    assert captured.get("gate_calls") == 1
    assert set(captured.get("members_ran") or []) == {"a", "b"}


def test_somatic_shadow_path_still_observes_without_side_effects():
    """The observe-only SHADOW path is preserved: ``tick(shadow=True)`` yields
    each member's side-effect-free output shape and never touches the old daemons'
    enabled state (kept for introspection/parity after the LIVE flip)."""
    from core.services import daemon_manager as dm

    before = {n: dm.is_enabled(n) for n in ("somatic", "experienced_time", "absence")}

    snap = {
        "somatic": {"energy_level": "medium", "somatic_phrase": "cpu 8%", "drain_score": 0.2},
        "experienced_time": {"felt_label": "kort", "session_event_count": 4, "base_minutes": 12.0},
        "absence": {"absence_label": "Det er stille her.", "absence_duration_hours": 0.5, "band": "short"},
    }
    with patch("core.services.event_gate.event_driven_enabled", return_value=True), \
         patch("core.services.event_gate.should_generative_fire", return_value=True), \
         patch("core.services.central_core.central"):
        result = cdm.build_somatic_family().tick(snap, shadow=True)

    after = {n: dm.is_enabled(n) for n in ("somatic", "experienced_time", "absence")}
    assert after == before, "shadow observe path must NOT change old-daemon enabled state"
    assert result["shadow"] is True
    assert set(result["members_ran"]) == {"somatic", "experienced_time", "absence"}
    # parity telemetry captured the members' output shapes
    assert result["outputs"]["somatic"]["phrase"] == "cpu 8%"
    assert result["outputs"]["absence"]["absence_label"] == "Det er stille her."


# ---------------------------------------------------------------------------
# somatic family — LIVE (default) end state: PRODUCES, not merely observes
# ---------------------------------------------------------------------------

_SOMATIC_SNAP = {
    "somatic": {"energy_level": "medium", "somatic_phrase": "cpu 8%"},
    "experienced_time": {"felt_label": "kort", "session_event_count": 4},
    "absence": {"absence_label": "Det er stille her.", "absence_duration_hours": 0.5},
    "energy_level": "medium",
    "event_count": 2,
    "new_signal_count": 1,
}


def _patch_somatic_live_ticks(stack):
    """Patch the 3 old tick_* daemons the somatic members dispatch to, and the
    absence DB seed, so LIVE runs exercise the real wiring without side effects."""
    from unittest.mock import MagicMock

    mocks = {
        "somatic": stack.enter_context(
            patch("core.services.somatic_daemon.tick_somatic_daemon",
                  MagicMock(return_value={"generated": True, "phrase": "cpu 8%"}))
        ),
        "experienced_time": stack.enter_context(
            patch("core.services.experienced_time_daemon.tick_experienced_time_daemon",
                  MagicMock(return_value={"felt_label": "kort", "session_event_count": 4}))
        ),
        "absence": stack.enter_context(
            patch("core.services.absence_daemon.tick_absence_daemon",
                  MagicMock(return_value={"generated": True, "label": "stille"}))
        ),
    }
    stack.enter_context(
        patch("core.services.absence_daemon.seed_last_interaction_from_db", MagicMock())
    )
    return mocks


def test_somatic_entrypoint_runs_live_by_default_and_produces():
    """tick_cluster_somatic defaults to LIVE: it CALLS the 3 old tick_* daemons
    (produces their outputs) rather than merely observing — and does so
    UNCONDITIONALLY (no generative gate; gate_calls=0)."""
    from contextlib import ExitStack

    with ExitStack() as stack:
        mocks = _patch_somatic_live_ticks(stack)
        stack.enter_context(patch("core.services.central_core.central"))
        stack.enter_context(patch.object(cdm, "_collect_somatic_snapshot", return_value=dict(_SOMATIC_SNAP)))
        result = cdm.tick_cluster_somatic()

    assert result["shadow"] is False
    assert result["gate_calls"] == 0
    assert result["fired"] is True
    assert set(result["members_ran"]) == {"somatic", "experienced_time", "absence"}
    for member, m in mocks.items():
        assert m.call_count == 1, f"{member} live generation not invoked"
    # the absence member bypasses its internal event-gate (family is the one point)
    _, kwargs = mocks["absence"].call_args
    assert kwargs.get("skip_event_gate") is True


def test_somatic_live_member_error_isolated_and_siblings_still_run():
    """A member's live tick raising must be captured, never propagated, and the
    sibling members must still produce."""
    from contextlib import ExitStack

    with ExitStack() as stack:
        mocks = _patch_somatic_live_ticks(stack)
        mocks["experienced_time"].side_effect = RuntimeError("felt-time boom")
        stack.enter_context(patch("core.services.central_core.central"))
        stack.enter_context(patch.object(cdm, "_collect_somatic_snapshot", return_value=dict(_SOMATIC_SNAP)))
        result = cdm.tick_cluster_somatic()

    assert "experienced_time" in result["member_errors"]
    assert "boom" in result["member_errors"]["experienced_time"]
    assert set(result["members_ran"]) == {"somatic", "absence"}


def test_somatic_entrypoint_never_raises_on_broken_family():
    """Catastrophic failure inside the family collapses to a minimal self-safe
    result — the heartbeat is never crashed."""
    with patch.object(cdm, "_collect_somatic_snapshot", side_effect=RuntimeError("collector down")):
        result = cdm.tick_cluster_somatic()
    assert result["family"] == "cluster_somatic"
    assert result["fired"] is False
    assert "__entry__" in result["member_errors"]


def test_somatic_live_flows_real_cache_to_surface():
    """End-to-end: a LIVE somatic tick updates the real module cache that
    build_body_state_surface()/get_latest_somatic_phrase() (load-bearing for
    cluster_innervoice/cluster_affect + visible_inner_life) serve to consumers."""
    from contextlib import ExitStack
    import core.services.somatic_daemon as sd

    with ExitStack() as stack:
        # real tick_somatic_daemon, but stub the raw-phrase builder + persistence
        stack.enter_context(patch.object(sd, "_build_raw_phrase", return_value="cpu 12% · rolig"))
        stack.enter_context(patch.object(sd, "raw_signal_mode_enabled", return_value=True))
        stack.enter_context(
            patch.object(sd, "_store_phrase",
                         side_effect=lambda phrase, snap: setattr(sd, "_cached_phrase", phrase))
        )
        stack.enter_context(patch("core.services.central_core.central"))
        # force _should_generate → True this tick
        sd._cached_phrase = ""
        sd._heartbeat_count_since_gen = 999
        snap = {"energy_level": "medium", "event_count": 1, "new_signal_count": 1,
                "somatic": {}, "experienced_time": {}, "absence": {}}
        # exercise the somatic member's LIVE dispatcher (calls tick_somatic_daemon)
        cdm._somatic_live(snap)

    assert sd.get_latest_somatic_phrase() == "cpu 12% · rolig"


# ---------------------------------------------------------------------------
# Registration + retirement of the 3 old daemons in daemon_manager
# ---------------------------------------------------------------------------


def test_cluster_somatic_registered_live():
    from core.services import daemon_manager as dm

    names = dm.get_daemon_names()
    assert "cluster_somatic" in names
    states = {d["name"]: d for d in dm.get_all_daemon_states()}
    entry = states["cluster_somatic"]
    assert entry["enabled"] is True
    assert "LIVE" in entry["description"]
    assert "SHADOW" not in entry["description"]


def test_three_old_somatic_daemons_retired():
    """somatic / experienced_time / absence are PENSIONERET (default disabled +
    retired marker) so their old is_enabled-gated heartbeat sites no-op."""
    from core.services import daemon_manager as dm

    retired = ["somatic", "experienced_time", "absence"]
    with patch.object(dm, "_load_state", return_value={}):
        for name in retired:
            assert dm._REGISTRY[name].get("default_enabled") is False, f"{name} must default disabled"
            assert dm._REGISTRY[name].get("retired") == "2026-07-15", f"{name} missing retired marker"
            assert "cluster_somatic" in dm._REGISTRY[name].get("description", ""), \
                f"{name} description must point at cluster_somatic"
            assert dm.is_enabled(name) is False, f"{name} must be disabled (retired)"
