"""Tests for Connections-cluster (connections) — forbindelses-livscyklus → Centralen.

Verificerer at presence + WS-events observes som metadata (ikke indhold), at active_summary
aggregerer, og at alt er self-safe.
"""
from __future__ import annotations

import pytest

from core.services import connections as cn


@pytest.fixture
def captured(monkeypatch):
    events = []
    monkeypatch.setattr(cn, "_observe", lambda nerve, data: events.append({"nerve": nerve, **data}))
    return events


def test_note_presence_metadata_only(captured):
    cn.note_presence("u1", "desk-abc", "linux", foreground=True, network="wifi")
    e = captured[0]
    assert e["nerve"] == "device_presence"
    assert e["user_id"] == "u1" and e["device"] == "desk-abc" and e["platform"] == "linux"
    # ingen indholds-felter lækket
    assert set(e.keys()) <= {"nerve", "user_id", "device", "platform", "foreground", "network"}


def test_note_ws_lifecycle(captured):
    cn.note_ws("connected", "127.0.0.1:5000")
    cn.note_ws("disconnected", "127.0.0.1:5000")
    assert captured[0]["event"] == "connected"
    assert captured[1]["event"] == "disconnected"


def test_self_safe_on_central_failure(monkeypatch):
    # _observe må aldrig kaste selv hvis central fejler
    import core.services.central_core as cc
    def boom():
        raise RuntimeError("nede")
    monkeypatch.setattr(cc, "central", boom)
    cn.note_presence("u", "d", "p")  # må ikke kaste
    cn.note_ws("connected", "x")


def test_active_summary_aggregates(monkeypatch):
    class _Rec:
        def __init__(self, nerve, payload):
            self.cluster = "connections"; self.nerve = nerve; self.payload = payload

    recs = [
        _Rec("device_presence", {"user_id": "u1", "device": "desk", "platform": "linux"}),
        _Rec("device_presence", {"user_id": "u2", "device": "mobile", "platform": "android"}),
        _Rec("device_presence", {"user_id": "u1", "device": "desk", "platform": "linux"}),  # dup
        _Rec("ws_connection", {"event": "connected"}),
        _Rec("ws_connection", {"event": "disconnected"}),
    ]

    class _Sink:
        def recent(self):
            return list(recs)

    import core.services.central_trace as ct
    monkeypatch.setattr(ct, "sink", lambda: _Sink())
    s = cn.active_summary()
    assert s["device_count"] == 2  # u1/desk dedupet
    assert s["ws_connected"] == 1 and s["ws_disconnected"] == 1


def test_connections_cluster_in_catalog():
    from core.services import central_catalog as cc
    assert cc.validate() == []
    assert "connections" in cc.clusters()
    names = [n.name for n in cc.by_cluster("connections")]
    assert "device_presence" in names and "ws_connection" in names


# ── Udvidelse: fejl-catcher + uautoriseret + session-aktivitet ───────────
def test_note_unauthorized_flags_incident(monkeypatch):
    from core.services import connections as cn
    obs = []
    monkeypatch.setattr(cn, "_observe", lambda nerve, data: obs.append({"nerve": nerve, **data}))
    flagged = {}
    monkeypatch.setattr("core.runtime.db_central_incidents.record_central_incident",
                        lambda **k: flagged.update(k))
    cn.note_unauthorized("uid-7", "s9", "tool:operator_bash", "tool_not_permitted", role="member")
    assert obs[0]["nerve"] == "unauthorized" and obs[0]["resource"] == "tool:operator_bash"
    # 6. jul: en forventet rolle-deny (tool_not_permitted) = error (gult), IKKE severe (rødt).
    # Gaten der virker skal ikke farve Centralen rød. Ægte anomalier forbliver severe.
    assert flagged["severity"] == "error" and flagged["nerve"] == "unauthorized"


def test_session_activity_combines_tools_and_unauthorized(monkeypatch):
    from core.services import connections as cn
    # tool_observer-del
    monkeypatch.setattr("core.services.tool_observer.recent_tool_calls",
                        lambda session_id=None, limit=300: [
                            {"tool": "read_file", "kind": "native", "status": "ok"},
                            {"tool": "operator_bash", "kind": "operator", "status": "error",
                             "error": "bridge_not_connected"},
                        ])

    class _Rec:
        def __init__(self, nerve, session_id, payload):
            self.cluster = "connections"; self.nerve = nerve
            self.session_id = session_id; self.payload = payload

    class _Sink:
        def recent(self):
            return [_Rec("unauthorized", "s1", {"resource": "tool:x",
                                                "reason": "tool_not_permitted"})]

    monkeypatch.setattr("core.services.central_trace.sink", lambda: _Sink())
    a = cn.session_activity("s1")
    assert {"tool": "read_file", "kind": "native"} in a["tools"]
    assert a["failed_tools"][0]["tool"] == "operator_bash"
    assert a["unauthorized"][0]["resource"] == "tool:x"


def test_connection_error_observed(monkeypatch):
    from core.services import connections as cn
    obs = []
    monkeypatch.setattr(cn, "_observe", lambda nerve, data: obs.append({"nerve": nerve, **data}))
    cn.note_connection_error("1.2.3.4:9", "ConnectionReset: broken pipe")
    assert obs[0]["nerve"] == "connection_error" and "broken pipe" in obs[0]["reason"]
