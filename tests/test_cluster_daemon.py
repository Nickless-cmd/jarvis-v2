"""Tests for the cluster-daemon primitive (spec 2026-07-14).

Verifies the load-reduction + safety invariants of :mod:`core.services.cluster_daemon`:
* the family runs its event-gate ONCE (not N times, one per member);
* a fired family dispatches to its members;
* a member error does NOT crash the family (self-safe);
* the somatic family runs in SHADOW without disabling the 3 old daemons, and
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


def test_somatic_family_defaults_to_shadow():
    """cluster_daemon_shadow defaults True → somatic family ticks observe-only."""
    with patch("core.runtime.db_core.get_runtime_state_value", return_value=None):
        assert cdm.shadow_mode_enabled() is True


def test_somatic_shadow_does_not_disable_old_daemons():
    """Running the somatic cluster in shadow leaves the 3 old daemons enabled."""
    from core.services import daemon_manager as dm

    before = {n: dm.is_enabled(n) for n in ("somatic", "experienced_time", "absence")}

    snap = {
        "somatic": {"energy_level": "medium", "somatic_phrase": "cpu 8%", "drain_score": 0.2},
        "experienced_time": {"felt_label": "kort", "session_event_count": 4, "base_minutes": 12.0},
        "absence": {"absence_label": "Det er stille her.", "absence_duration_hours": 0.5, "band": "short"},
    }
    with patch("core.services.event_gate.event_driven_enabled", return_value=True), \
         patch("core.services.event_gate.should_generative_fire", return_value=True), \
         patch("core.services.central_core.central") as _c:
        result = cdm.build_somatic_family().tick(snap, shadow=True)

    after = {n: dm.is_enabled(n) for n in ("somatic", "experienced_time", "absence")}
    assert after == before, "shadow cluster must NOT change old-daemon enabled state"
    assert result["shadow"] is True
    assert set(result["members_ran"]) == {"somatic", "experienced_time", "absence"}
    # parity telemetry captured the members' output shapes
    assert result["outputs"]["somatic"]["phrase"] == "cpu 8%"
    assert result["outputs"]["absence"]["absence_label"] == "Det er stille her."


def test_somatic_family_registered_and_shadow_marked():
    from core.services import daemon_manager as dm

    names = dm.get_daemon_names()
    assert "cluster_somatic" in names
    states = {d["name"]: d for d in dm.get_all_daemon_states()}
    entry = states["cluster_somatic"]
    assert entry["enabled"] is True
    assert "SHADOW" in entry["description"]
