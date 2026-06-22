"""Tests for Agents-cluster (agents) — multi-agent-systemerne synlige i Centralen."""
from __future__ import annotations

import pytest

from core.services import agents as ag


@pytest.fixture
def captured(monkeypatch):
    events = []
    monkeypatch.setattr(ag, "_observe", lambda nerve, data: events.append({"nerve": nerve, **data}))
    return events


def test_note_agent_spawn(captured):
    ag.note_agent_spawn("agent-1", "reviewer", parent="jarvis", council_id="c1", mode="swarm")
    e = captured[0]
    assert e["nerve"] == "agent_spawn" and e["agent_id"] == "agent-1"
    assert e["role"] == "reviewer" and e["council_id"] == "c1" and e["mode"] == "swarm"


def test_note_council_outcome(captured):
    ag.note_council("skal vi refaktorere X?", rounds=4, deadlocked=True,
                    escalated=True, recruited="devils_advocate")
    e = captured[0]
    assert e["nerve"] == "council_session" and e["rounds"] == 4
    assert e["deadlocked"] is True and e["escalated"] is True


def test_note_agent_error(captured):
    ag.note_agent_error("agent-2", RuntimeError("spawn failed"))
    assert captured[0]["nerve"] == "agent_error" and "RuntimeError" in captured[0]["error"]


def test_self_safe_on_central_failure(monkeypatch):
    import core.services.central_core as cc
    monkeypatch.setattr(cc, "central", lambda: (_ for _ in ()).throw(RuntimeError("nede")))
    ag.note_agent_spawn("a", "r")  # må ikke kaste
    ag.note_council("t", rounds=1)


def test_agents_summary_aggregates(monkeypatch):
    class _Rec:
        def __init__(self, nerve, payload=None):
            self.cluster = "agents"; self.nerve = nerve; self.payload = payload or {}

    class _Sink:
        def recent(self, limit=500):
            return [_Rec("agent_spawn"), _Rec("agent_spawn"), _Rec("agent_error"),
                    _Rec("council_session", {"deadlocked": True}),
                    _Rec("council_session", {"deadlocked": False})]

    import core.services.central_trace as ct
    monkeypatch.setattr(ct, "sink", lambda: _Sink())
    s = ag.agents_summary()
    assert s["agent_spawns"] == 2 and s["agent_errors"] == 1
    assert s["council_sessions"] == 2 and s["council_deadlocks"] == 1


def test_agents_cluster_in_catalog():
    from core.services import central_catalog as cc
    assert cc.validate() == []
    assert "agents" in cc.clusters()
    names = [n.name for n in cc.by_cluster("agents")]
    assert "agent_spawn" in names and "council_session" in names
