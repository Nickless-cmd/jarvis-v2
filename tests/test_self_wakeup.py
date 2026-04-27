"""Unit tests for self_wakeup."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import core.services.self_wakeup as sw


def test_schedule_validates_prompt(monkeypatch):
    monkeypatch.setattr(sw, "_load", lambda: [])
    monkeypatch.setattr(sw, "_save", lambda r: None)
    result = sw.schedule_self_wakeup(delay_seconds=120, prompt="")
    assert result["status"] == "error"


def test_schedule_clamps_delay(monkeypatch):
    state: list = []
    monkeypatch.setattr(sw, "_load", lambda: list(state))
    monkeypatch.setattr(sw, "_save", lambda r: state.clear() or state.extend(r))
    # Below min
    result = sw.schedule_self_wakeup(delay_seconds=10, prompt="x")
    assert result["wakeup"]["delay_seconds"] == 60
    # Above max
    state.clear()
    result = sw.schedule_self_wakeup(delay_seconds=999999, prompt="x")
    assert result["wakeup"]["delay_seconds"] == 86400


def test_schedule_persists(monkeypatch):
    state: list = []
    monkeypatch.setattr(sw, "_load", lambda: list(state))
    monkeypatch.setattr(sw, "_save", lambda r: state.clear() or state.extend(r))
    result = sw.schedule_self_wakeup(delay_seconds=120, prompt="resume X", reason="test")
    assert result["status"] == "ok"
    assert result["wakeup"]["status"] == "pending"
    assert "resume X" in result["wakeup"]["prompt"]
    assert len(state) == 1


def test_max_pending_limit(monkeypatch):
    state = [{"wakeup_id": f"w{i}", "status": "pending"} for i in range(20)]
    monkeypatch.setattr(sw, "_load", lambda: list(state))
    monkeypatch.setattr(sw, "_save", lambda r: None)
    result = sw.schedule_self_wakeup(delay_seconds=120, prompt="x")
    assert result["status"] == "error"
    assert "max 20" in result["error"]


def test_due_wakeups_marks_fired(monkeypatch):
    past = (datetime.now(UTC) - timedelta(seconds=10)).isoformat()
    future = (datetime.now(UTC) + timedelta(seconds=300)).isoformat()
    state = [
        {"wakeup_id": "w1", "status": "pending", "fire_at": past, "prompt": "p1", "reason": "r1"},
        {"wakeup_id": "w2", "status": "pending", "fire_at": future, "prompt": "p2", "reason": ""},
    ]
    monkeypatch.setattr(sw, "_load", lambda: list(state))
    monkeypatch.setattr(sw, "_save", lambda r: state.clear() or state.extend(r))
    due = sw.due_wakeups()
    ids = [r["wakeup_id"] for r in due]
    assert "w1" in ids
    assert "w2" not in ids
    # w1 should now be marked fired in state
    w1 = next(r for r in state if r["wakeup_id"] == "w1")
    assert w1["status"] == "fired"


def test_mark_consumed(monkeypatch):
    state = [{"wakeup_id": "w1", "status": "fired", "prompt": "p", "reason": ""}]
    monkeypatch.setattr(sw, "_load", lambda: list(state))
    monkeypatch.setattr(sw, "_save", lambda r: state.clear() or state.extend(r))
    result = sw.mark_wakeup_consumed("w1")
    assert result["status"] == "ok"
    assert state[0]["status"] == "consumed"


def test_cancel_pending(monkeypatch):
    state = [{"wakeup_id": "w1", "status": "pending"}]
    monkeypatch.setattr(sw, "_load", lambda: list(state))
    monkeypatch.setattr(sw, "_save", lambda r: state.clear() or state.extend(r))
    result = sw.cancel_wakeup("w1")
    assert result["status"] == "ok"
    assert state[0]["status"] == "cancelled"


def test_cancel_fired_fails(monkeypatch):
    state = [{"wakeup_id": "w1", "status": "fired"}]
    monkeypatch.setattr(sw, "_load", lambda: list(state))
    monkeypatch.setattr(sw, "_save", lambda r: None)
    result = sw.cancel_wakeup("w1")
    assert result["status"] == "error"


def test_section_returns_none_when_no_fired(monkeypatch):
    monkeypatch.setattr(sw, "due_wakeups", lambda **kw: [])
    assert sw.self_wakeup_section() is None


def test_section_lists_fired_wakeups(monkeypatch):
    monkeypatch.setattr(sw, "due_wakeups", lambda **kw: [
        {"wakeup_id": "w1", "status": "fired",
         "prompt": "Tjek om brugeren er klar", "reason": "follow-up"},
    ])
    section = sw.self_wakeup_section()
    assert section is not None
    assert "Tjek om brugeren er klar" in section
    assert "follow-up" in section
