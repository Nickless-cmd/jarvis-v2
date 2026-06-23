"""Tests for real-time Central-surface (owner-vindue)."""
from __future__ import annotations

from core.services import central_realtime as cr


def test_snapshot_shape_self_safe():
    s = cr.realtime_snapshot()
    for k in ("status", "coverage", "diagnose", "feed", "incidents",
              "open_breakers", "learning"):
        assert k in s
    assert s["status"] in ("green", "yellow", "red")
    assert isinstance(s["feed"], list)


def test_status_red_on_open_breaker():
    st = cr._status_from({"degraded": False}, [], ["auth/tool_access"], {}, [])
    assert st == "red"


def test_status_red_on_severe_incident():
    st = cr._status_from({"degraded": False}, [{"severity": "severe"}], [], {}, [])
    assert st == "red"


def test_status_red_on_fail_open():
    st = cr._status_from({"degraded": False}, [{"kind": "fail_open", "severity": "error"}], [], {}, [])
    assert st == "red"


def test_status_yellow_on_degrading():
    st = cr._status_from({"degraded": False}, [], [], {}, [{"cluster": "x", "nerve": "y"}])
    assert st == "yellow"


def test_status_green_when_clean():
    st = cr._status_from({"degraded": False}, [], [], {}, [])
    assert st == "green"
