"""Tests for daemon-helbred (Fase 1) — standalone/listener-fejl synlige i Centralen."""
from __future__ import annotations

from core.services import daemon_health as dh


def test_note_error_emits(monkeypatch):
    captured = {}

    class _Central:
        def observe(self, event):
            captured.update(event)

    import core.services.central_core as cc
    monkeypatch.setattr(cc, "central", lambda: _Central())
    dh.note_error("agency_cartographer", RuntimeError("scan failed"))
    assert captured["cluster"] == "system" and captured["nerve"] == "daemon_health"
    assert captured["daemon"] == "agency_cartographer" and captured["ok"] is False
    assert "RuntimeError" in captured["error"]


def test_note_error_self_safe(monkeypatch):
    import core.services.central_core as cc
    def boom():
        raise RuntimeError("nede")
    monkeypatch.setattr(cc, "central", boom)
    dh.note_error("x", ValueError("y"))  # må ikke kaste


def test_summary_aggregates_failures(monkeypatch):
    class _Rec:
        def __init__(self, daemon, ok):
            self.cluster = "system"; self.nerve = "daemon_health"
            self.payload = {"daemon": daemon, "ok": ok}

    class _Sink:
        def recent(self):
            return [_Rec("a", False), _Rec("a", False), _Rec("b", False), _Rec("c", True)]

    import core.services.central_trace as ct
    monkeypatch.setattr(ct, "sink", lambda: _Sink())
    s = dh.daemon_health_summary()
    assert s["failing_daemons"] == {"a": 2, "b": 1}
    assert s["failing_count"] == 2


def test_daemon_health_in_catalog():
    from core.services import central_catalog as cc
    assert cc.validate() == []
    names = [n.name for n in cc.by_cluster("system")]
    assert "daemon_health" in names
