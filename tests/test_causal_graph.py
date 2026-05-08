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


def test_publish_with_explicit_caused_by_writes_edge():
    from core.eventbus.bus import event_bus
    from core.runtime.db import connect, _ensure_causal_edges_table
    with connect() as c:
        _ensure_causal_edges_table(c)
        cur = c.execute(
            "INSERT INTO events (kind, payload_json, created_at) VALUES "
            "('runtime.test_parent', '{}', '2026-05-08T00:00:00Z')"
        )
        parent_id = int(cur.lastrowid)
        c.commit()
    event_bus.publish(
        "runtime.test_child",
        {"x": 1},
        caused_by=parent_id,
        edge_kind="triggered",
    )
    with connect() as c:
        rows = c.execute(
            "SELECT * FROM causal_edges WHERE parent_event_id = ?",
            (parent_id,),
        ).fetchall()
    assert len(rows) == 1
    assert rows[0]["edge_kind"] == "triggered"
    assert rows[0]["source"] == "explicit"
    assert rows[0]["confidence"] == 1.0


def test_publish_auto_pickup_from_event_context():
    from core.eventbus.bus import event_bus
    from core.eventbus.context import with_event_context
    from core.runtime.db import connect, _ensure_causal_edges_table
    with connect() as c:
        _ensure_causal_edges_table(c)
        cur = c.execute(
            "INSERT INTO events (kind, payload_json, created_at) VALUES "
            "('runtime.ctx_parent', '{}', '2026-05-08T00:00:00Z')"
        )
        parent_id = int(cur.lastrowid)
        c.commit()
    with with_event_context(parent_id):
        event_bus.publish("runtime.ctx_child", {"y": 2})
    with connect() as c:
        rows = c.execute(
            "SELECT * FROM causal_edges WHERE parent_event_id = ?",
            (parent_id,),
        ).fetchall()
    assert len(rows) == 1
    assert rows[0]["source"] == "explicit"
    assert rows[0]["edge_kind"] == "triggered"


def test_publish_explicit_overrides_context():
    from core.eventbus.bus import event_bus
    from core.eventbus.context import with_event_context
    from core.runtime.db import connect, _ensure_causal_edges_table
    with connect() as c:
        _ensure_causal_edges_table(c)
        c.execute(
            "INSERT INTO events (kind, payload_json, created_at) VALUES "
            "('runtime.override_ctx', '{}', '2026-05-08T00:00:00Z')"
        )
        ctx_id = int(c.execute("SELECT last_insert_rowid()").fetchone()[0])
        c.execute(
            "INSERT INTO events (kind, payload_json, created_at) VALUES "
            "('runtime.override_explicit', '{}', '2026-05-08T00:00:00Z')"
        )
        explicit_id = int(c.execute("SELECT last_insert_rowid()").fetchone()[0])
        c.commit()
    with with_event_context(ctx_id):
        event_bus.publish(
            "runtime.override_child",
            {"z": 3},
            caused_by=explicit_id,
        )
    with connect() as c:
        rows = c.execute(
            "SELECT parent_event_id FROM causal_edges "
            "WHERE parent_event_id IN (?, ?)",
            (ctx_id, explicit_id),
        ).fetchall()
    parents = {int(r["parent_event_id"]) for r in rows}
    assert parents == {explicit_id}, f"explicit should override context: {parents}"


def test_publish_caused_by_list_creates_multiple_edges():
    from core.eventbus.bus import event_bus
    from core.runtime.db import connect, _ensure_causal_edges_table
    with connect() as c:
        _ensure_causal_edges_table(c)
        c.execute(
            "INSERT INTO events (kind, payload_json, created_at) VALUES "
            "('runtime.multi_p1', '{}', '2026-05-08T00:00:00Z')"
        )
        p1 = int(c.execute("SELECT last_insert_rowid()").fetchone()[0])
        c.execute(
            "INSERT INTO events (kind, payload_json, created_at) VALUES "
            "('runtime.multi_p2', '{}', '2026-05-08T00:00:00Z')"
        )
        p2 = int(c.execute("SELECT last_insert_rowid()").fetchone()[0])
        c.commit()
    event_bus.publish(
        "runtime.multi_child", {"v": 1}, caused_by=[p1, p2],
    )
    with connect() as c:
        rows = c.execute(
            "SELECT parent_event_id FROM causal_edges "
            "WHERE parent_event_id IN (?, ?)", (p1, p2),
        ).fetchall()
    assert {int(r["parent_event_id"]) for r in rows} == {p1, p2}
