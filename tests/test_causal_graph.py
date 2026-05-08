"""Causal graph Phase 1 — comprehensive tests.

Tests are intentionally NOT isolated (no fixtures wiping the table)
because we exercise idempotency + persistence properties on the real DB.
Each test that creates rows uses identifying tags so reruns don't pile up.
"""
from __future__ import annotations


def test_causal_edges_table_exists_with_correct_schema():
    from core.runtime.db import connect, _ensure_causal_edges_table
    with connect() as c:
        _ensure_causal_edges_table(c)
        cols = {r["name"]: r["type"] for r in c.execute(
            "PRAGMA table_info(causal_edges)"
        ).fetchall()}
    assert "child_event_id" in cols
    assert "parent_event_id" in cols
    assert "edge_kind" in cols
    assert "confidence" in cols
    assert "source" in cols
    assert "reasoning" in cols
    assert "created_at" in cols


def test_causal_edges_unique_constraint():
    from core.runtime.db import connect, _ensure_causal_edges_table
    with connect() as c:
        _ensure_causal_edges_table(c)
        c.execute(
            "INSERT INTO causal_edges (child_event_id, parent_event_id, "
            "edge_kind, confidence, source, created_at) "
            "VALUES (1, 2, 'triggered', 1.0, 'explicit', '2026-05-08T00:00:00Z')"
        )
        # Insert duplicate — should fail via UNIQUE constraint
        import sqlite3
        try:
            c.execute(
                "INSERT INTO causal_edges (child_event_id, parent_event_id, "
                "edge_kind, confidence, source, created_at) "
                "VALUES (1, 2, 'triggered', 0.9, 'inferred-kind', '2026-05-08T00:00:01Z')"
            )
            assert False, "expected UNIQUE constraint violation"
        except sqlite3.IntegrityError:
            pass
        # Cleanup so test is rerunnable
        c.execute("DELETE FROM causal_edges WHERE child_event_id = 1")


def test_event_context_default_is_none():
    from core.eventbus.context import get_current_event
    assert get_current_event() is None


def test_event_context_set_and_reset():
    from core.eventbus.context import set_current_event, get_current_event
    token = set_current_event(42)
    try:
        assert get_current_event() == 42
    finally:
        from core.eventbus.context import _current_event_context
        _current_event_context.reset(token)
    assert get_current_event() is None


def test_event_context_with_helper():
    from core.eventbus.context import with_event_context, get_current_event
    assert get_current_event() is None
    with with_event_context(99):
        assert get_current_event() == 99
        with with_event_context(100):
            assert get_current_event() == 100
        assert get_current_event() == 99
    assert get_current_event() is None
