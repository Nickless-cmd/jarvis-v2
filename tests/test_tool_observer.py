"""Tests for Tools-cluster query-helpers (tool_observer).

Verificerer at native/operator/session/status-filtrering virker mod en syntetisk trace,
og at fejl-indgangen kun returnerer fejlede kald — debugging af "fejl ude af huset".
"""
from __future__ import annotations

import pytest

from core.services import tool_observer as to


class _Rec:
    def __init__(self, session_id, payload):
        self.cluster = "tools"
        self.nerve = "tool_call"
        self.session_id = session_id
        self.payload = payload


@pytest.fixture
def fake_trace(monkeypatch):
    recs = [
        _Rec("s1", {"tool": "read_file", "kind": "native", "role": "owner",
                    "scope": "chat", "status": "ok", "error": ""}),
        _Rec("s2", {"tool": "operator_bash", "kind": "operator", "role": "member",
                    "scope": "code", "status": "error", "error": "bridge_not_connected"}),
        _Rec("s1", {"tool": "operator_write_file", "kind": "operator", "role": "owner",
                    "scope": "code", "status": "error", "error": "path denied"}),
    ]

    class _Sink:
        def recent(self):
            return list(recs)

    import core.services.central_trace as ct
    monkeypatch.setattr(ct, "sink", lambda: _Sink())
    return recs


def test_recent_calls_all(fake_trace):
    assert len(to.recent_tool_calls(limit=100)) == 3


def test_filter_by_session(fake_trace):
    s1 = to.recent_tool_calls(session_id="s1", limit=100)
    assert len(s1) == 2
    assert all(c["session_id"] == "s1" for c in s1)


def test_filter_by_kind_operator(fake_trace):
    ops = to.recent_tool_calls(kind="operator", limit=100)
    assert len(ops) == 2
    assert all(c["kind"] == "operator" for c in ops)


def test_failures_only(fake_trace):
    fails = to.recent_tool_failures(limit=100)
    assert len(fails) == 2
    assert all(c["status"] == "error" for c in fails)


def test_failures_operator_in_session(fake_trace):
    # præcis debugging: hvilket operator-tool fejlede i session s2?
    f = to.recent_tool_failures(session_id="s2", kind="operator")
    assert len(f) == 1
    assert f[0]["tool"] == "operator_bash"
    assert "bridge_not_connected" in f[0]["error"]


def test_summary(fake_trace):
    s = to.tool_call_summary()
    assert s["total"] == 3 and s["operator"] == 2 and s["native"] == 1
    assert s["failures"] == 2
    assert "operator_bash" in s["failing_tools"]


def test_catalog_validates_with_tools():
    from core.services import central_catalog as cc
    assert cc.validate() == []
    assert "tools" in cc.clusters()
