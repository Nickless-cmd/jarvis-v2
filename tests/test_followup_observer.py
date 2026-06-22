"""Tests for Followup-cluster (followup_observer) — agentisk loop synlig i Centralen."""
from __future__ import annotations

import pytest

from core.services import followup_observer as fo


@pytest.fixture
def captured(monkeypatch):
    events = []
    monkeypatch.setattr(fo, "_observe",
                        lambda nerve, run_id, **d: events.append({"nerve": nerve, "run_id": run_id, **d}))
    return events


def test_note_round(captured):
    fo.note_round("r1", 2, "deepseek", "deepseek-v4-flash:cloud", exchanges=3)
    e = captured[0]
    assert e["nerve"] == "followup_round" and e["round_num"] == 2
    assert e["provider"] == "deepseek" and e["exchanges"] == 3


def test_note_round_failed_truncates_error(captured):
    fo.note_round_failed("r1", 1, "github-copilot", "x" * 400)
    e = captured[0]
    assert e["nerve"] == "followup_failed" and e["provider"] == "github-copilot"
    assert len(e["error"]) <= 200


def test_note_loop_complete(captured):
    fo.note_loop_complete("r1", rounds=4, exit_reason="completed", provider="p", model="m")
    e = captured[0]
    assert e["nerve"] == "followup_loop_complete" and e["rounds"] == 4
    assert e["exit_reason"] == "completed"


def test_self_safe_on_central_failure(monkeypatch):
    import core.services.central_core as cc
    monkeypatch.setattr(cc, "central", lambda: (_ for _ in ()).throw(RuntimeError("nede")))
    fo.note_round("r", 1)            # må ikke kaste
    fo.note_round_failed("r", 1)
    fo.note_loop_complete("r", rounds=1)


def test_followup_summary_aggregates_avg(monkeypatch):
    class _Rec:
        def __init__(self, nerve, payload=None):
            self.cluster = "loop"; self.nerve = nerve; self.payload = payload or {}

    class _Sink:
        def recent(self, limit=500):
            return [_Rec("followup_round"), _Rec("followup_round"), _Rec("followup_failed"),
                    _Rec("followup_loop_complete", {"rounds": 4}),
                    _Rec("followup_loop_complete", {"rounds": 2}),
                    _Rec("tool_budget")]  # andet loop-nerve ignoreres i tællingen

    import core.services.central_trace as ct
    monkeypatch.setattr(ct, "sink", lambda: _Sink())
    s = fo.followup_summary()
    assert s["followup_rounds"] == 2 and s["followup_failures"] == 1
    assert s["followup_loops"] == 2 and s["avg_rounds_per_loop"] == 3.0


def test_followup_nerves_in_catalog():
    from core.services import central_catalog as cc
    assert cc.validate() == []
    names = [n.name for n in cc.by_cluster("loop")]
    assert "followup_round" in names and "followup_failed" in names
    assert "followup_loop_complete" in names
