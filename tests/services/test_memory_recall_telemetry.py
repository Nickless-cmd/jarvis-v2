"""Tests for memory_recall_telemetry (Phase 2 prep for Lag 11)."""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from core.services import memory_recall_telemetry as mrt


def _setup_db(monkeypatch, rows):
    """Replace connect() to point at an in-memory events table."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE events (id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "kind TEXT, payload_json TEXT DEFAULT '{}', created_at TEXT)"
    )
    for kind, payload_json, created_at in rows:
        conn.execute(
            "INSERT INTO events(kind, payload_json, created_at) VALUES (?, ?, ?)",
            (kind, payload_json, created_at),
        )
    conn.commit()

    class _Ctx:
        def __enter__(self):
            return conn
        def __exit__(self, *a):
            pass
    monkeypatch.setattr("core.runtime.db.connect", lambda: _Ctx())


def test_count_recent_returns_total(monkeypatch):
    now = datetime.now(UTC)
    rows = [
        ("memory.recall_empty", '{"tool":"search_memory"}', (now - timedelta(hours=2)).isoformat()),
        ("memory.recall_empty", '{"tool":"search_sessions"}', (now - timedelta(hours=5)).isoformat()),
        ("memory.recall_empty", '{"tool":"search_memory"}', (now - timedelta(hours=20)).isoformat()),
        ("memory.recall_empty", '{"tool":"search_memory"}', (now - timedelta(hours=48)).isoformat()),
        ("tool.completed", '{"tool":"x"}', now.isoformat()),  # different kind, ignored
    ]
    _setup_db(monkeypatch, rows)
    r = mrt.count_recent_recall_empty(hours=24)
    assert r["status"] == "ok"
    assert r["total"] == 3  # 48h-old row is outside 24h window


def test_count_recent_by_tool_breakdown(monkeypatch):
    now = datetime.now(UTC)
    rows = [
        ("memory.recall_empty", '{"tool":"search_memory"}', (now - timedelta(hours=2)).isoformat()),
        ("memory.recall_empty", '{"tool":"search_memory"}', (now - timedelta(hours=3)).isoformat()),
        ("memory.recall_empty", '{"tool":"search_sessions"}', (now - timedelta(hours=5)).isoformat()),
        ("memory.recall_empty", '{"tool":"search_chat_history"}', (now - timedelta(hours=6)).isoformat()),
    ]
    _setup_db(monkeypatch, rows)
    r = mrt.count_recent_recall_empty(hours=24, by_tool=True)
    assert r["total"] == 4
    assert r["by_tool"]["search_memory"] == 2
    assert r["by_tool"]["search_sessions"] == 1
    assert r["by_tool"]["search_chat_history"] == 1


def test_count_recent_clamps_hours():
    # 0 or negative gets clamped to >= 1
    r = mrt.count_recent_recall_empty(hours=0)
    assert r["window_hours"] == 1
    # Very large gets clamped
    r = mrt.count_recent_recall_empty(hours=10000)
    assert r["window_hours"] == 720  # 30 days


def test_emit_is_fire_and_forget(monkeypatch):
    """emit_recall_empty never raises even when eventbus fails."""
    def _boom(*a, **kw):
        raise RuntimeError("eventbus is dead")
    monkeypatch.setattr("core.eventbus.bus.event_bus.publish", _boom)
    # Should not raise
    mrt.emit_recall_empty(tool="search_memory", query="test")


def test_emit_truncates_long_query(monkeypatch):
    """emit_recall_empty caps query length to 200 chars."""
    captured = {}
    def _capture(kind, payload, **kw):
        captured["kind"] = kind
        captured["payload"] = payload
    monkeypatch.setattr("core.eventbus.bus.event_bus.publish", _capture)
    long_query = "x" * 1000
    mrt.emit_recall_empty(tool="search_memory", query=long_query)
    assert captured["kind"] == "memory.recall_empty"
    assert len(captured["payload"]["query"]) == 200


def test_emit_includes_month_key(monkeypatch):
    captured = {}
    def _capture(kind, payload, **kw):
        captured["payload"] = payload
    monkeypatch.setattr("core.eventbus.bus.event_bus.publish", _capture)
    mrt.emit_recall_empty(tool="search_memory", query="test")
    month_key = captured["payload"]["month_key"]
    # YYYY-MM format
    assert len(month_key) == 7
    assert month_key[4] == "-"


def test_surface_returns_active(monkeypatch):
    _setup_db(monkeypatch, [])
    s = mrt.build_memory_recall_telemetry_surface()
    assert s["active"] is True
    assert s["mode"] == "memory_recall_telemetry"
    assert "0 recall-empty events" in s["summary"]
