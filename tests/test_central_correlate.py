"""Tests for cross-cluster korrelation (central_correlate) — én klar linje pr. run_id."""
from __future__ import annotations

import pytest

from core.services import central_correlate as corr


class _Rec:
    def __init__(self, run_id, cluster, nerve, kind="decide", decision="", reason="", latency_ms=0):
        self.run_id = run_id; self.cluster = cluster; self.nerve = nerve
        self.kind = kind; self.decision = decision; self.reason = reason
        self.latency_ms = latency_ms


@pytest.fixture
def mock_sink(monkeypatch):
    records = []

    class _Sink:
        def records_for_run(self, rid):
            return [r for r in records if r.run_id == rid]

        def recent(self, limit=50):
            return records[-limit:]

    import core.services.central_trace as ct
    monkeypatch.setattr(ct, "sink", lambda: _Sink())
    # nerve_location → en kendt fil for at teste fil-mapping
    import core.services.central_catalog as cc
    monkeypatch.setattr(cc, "nerve_location",
                        lambda n: {"tool_access": "core/services/gate_auth.py"}.get(n, ""))
    return records


def test_correlate_builds_timeline_across_clusters(mock_sink):
    mock_sink.extend([
        _Rec("r1", "loop", "loop_control", decision="green"),
        _Rec("r1", "truth", "truth", decision="green"),
        _Rec("r1", "auth", "tool_access", decision="red", reason="ikke tilladt"),
    ])
    out = corr.correlate("r1")
    assert out["events"] == 3
    assert out["clusters_touched"] == ["auth", "loop", "truth"]
    # break-point = første RED (auth/tool_access)
    assert out["break_point"]["cluster"] == "auth"
    assert out["break_point"]["nerve"] == "tool_access"
    # fil-mapping fra kataloget
    assert "core/services/gate_auth.py" in out["files"]


def test_break_point_on_error_kind(mock_sink):
    mock_sink.extend([
        _Rec("r2", "stream", "provider_call", kind="observe", decision="green"),
        _Rec("r2", "memory", "memory_recall", kind="error", reason="gather-fejl"),
    ])
    out = corr.correlate("r2")
    assert out["break_point"]["kind"] == "error"
    assert out["break_point"]["cluster"] == "memory"


def test_no_break_when_all_green(mock_sink):
    mock_sink.append(_Rec("r3", "loop", "loop_control", decision="green"))
    out = corr.correlate("r3")
    assert out["break_point"] is None


def test_empty_run_id(mock_sink):
    assert corr.correlate("")["events"] == 0


def test_recent_broken_runs(mock_sink):
    mock_sink.extend([
        _Rec("ra", "loop", "loop_control", decision="green"),
        _Rec("rb", "auth", "tool_access", decision="red", reason="deny"),
        _Rec("rc", "memory", "x", kind="error", reason="boom"),
    ])
    broken = corr.recent_broken_runs()
    rids = {b["run_id"] for b in broken}
    assert rids == {"rb", "rc"}  # ra var grøn
