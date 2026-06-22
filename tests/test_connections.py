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
