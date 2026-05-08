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


def _setup_chain_a_b_c():
    """Build a deterministic A→B→C chain. Returns (a_id, b_id, c_id)."""
    from core.runtime.db import connect, _ensure_causal_edges_table
    from core.eventbus.bus import event_bus
    with connect() as c:
        _ensure_causal_edges_table(c)
        c.execute(
            "INSERT INTO events (kind, payload_json, created_at) VALUES "
            "('runtime.chain_a', '{}', '2026-05-08T00:00:00Z')"
        )
        a = int(c.execute("SELECT last_insert_rowid()").fetchone()[0])
        c.commit()
    event_bus.publish("runtime.chain_b", {}, caused_by=a)
    with connect() as c:
        b = int(c.execute(
            "SELECT id FROM events WHERE kind='runtime.chain_b' "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()[0])
    event_bus.publish("runtime.chain_c", {}, caused_by=b)
    with connect() as c:
        ch = int(c.execute(
            "SELECT id FROM events WHERE kind='runtime.chain_c' "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()[0])
    return a, b, ch


def test_query_causal_chain_backward_traversal():
    from core.services.causal_graph import query_causal_chain
    a, b, c = _setup_chain_a_b_c()
    result = query_causal_chain(event_id=c, direction="backward", max_depth=5)
    assert result["root_event"]["id"] == c
    chain_ids = [step["event"]["id"] for step in result["chain"]]
    assert chain_ids == [b, a]
    assert result["truncated_by_depth"] is False
    assert result["total_nodes_returned"] == 2


def test_query_causal_chain_forward_traversal():
    from core.services.causal_graph import query_causal_chain
    a, b, c = _setup_chain_a_b_c()
    result = query_causal_chain(event_id=a, direction="forward", max_depth=5)
    chain_ids = [step["event"]["id"] for step in result["chain"]]
    assert b in chain_ids
    assert c in chain_ids


def test_query_causal_chain_max_depth_truncates():
    from core.services.causal_graph import query_causal_chain
    a, b, c = _setup_chain_a_b_c()
    result = query_causal_chain(event_id=c, direction="backward", max_depth=1)
    assert result["truncated_by_depth"] is True
    assert result["total_nodes_returned"] == 1


def test_query_causal_chain_no_edges_returns_empty_chain():
    from core.runtime.db import connect, _ensure_causal_edges_table
    from core.services.causal_graph import query_causal_chain
    with connect() as c:
        _ensure_causal_edges_table(c)
        c.execute(
            "INSERT INTO events (kind, payload_json, created_at) VALUES "
            "('runtime.lonely', '{}', '2026-05-08T00:00:00Z')"
        )
        lonely = int(c.execute("SELECT last_insert_rowid()").fetchone()[0])
        c.commit()
    result = query_causal_chain(event_id=lonely, direction="backward")
    assert result["chain"] == []
    assert result["root_event"]["id"] == lonely


def test_query_causal_chain_handles_cycle_gracefully():
    from core.runtime.db import connect, _ensure_causal_edges_table
    from core.services.causal_graph import query_causal_chain
    with connect() as c:
        _ensure_causal_edges_table(c)
        c.execute(
            "INSERT INTO events (kind, payload_json, created_at) VALUES "
            "('runtime.cycle_a', '{}', '2026-05-08T00:00:00Z')"
        )
        a = int(c.execute("SELECT last_insert_rowid()").fetchone()[0])
        c.execute(
            "INSERT INTO events (kind, payload_json, created_at) VALUES "
            "('runtime.cycle_b', '{}', '2026-05-08T00:00:00Z')"
        )
        b = int(c.execute("SELECT last_insert_rowid()").fetchone()[0])
        c.execute(
            "INSERT INTO causal_edges (child_event_id, parent_event_id, "
            "edge_kind, confidence, source, created_at) VALUES "
            "(?, ?, 'triggered', 1.0, 'explicit', '2026-05-08T00:00:00Z')",
            (b, a),
        )
        c.execute(
            "INSERT INTO causal_edges (child_event_id, parent_event_id, "
            "edge_kind, confidence, source, created_at) VALUES "
            "(?, ?, 'triggered', 1.0, 'explicit', '2026-05-08T00:00:01Z')",
            (a, b),
        )
        c.commit()
    result = query_causal_chain(event_id=a, direction="backward", max_depth=10)
    assert isinstance(result, dict)


def test_query_causal_chain_pagination():
    from core.services.causal_graph import query_causal_chain
    a, b, c = _setup_chain_a_b_c()
    result = query_causal_chain(
        event_id=c, direction="backward", max_depth=5, limit=1, offset=0,
    )
    assert result["total_nodes_returned"] == 1
    assert result["truncated_by_limit"] is True
    assert result["next_offset"] == 1


def _insert_event_with_payload(kind: str, payload: dict, ts: str) -> int:
    """Insert event. Tests should use _recent_ts() helper for ts so the
    daemon's default lookback window picks up the synthetic event.
    """
    import json as _json
    from core.runtime.db import connect
    with connect() as c:
        cur = c.execute(
            "INSERT INTO events (kind, payload_json, created_at) VALUES (?, ?, ?)",
            (kind, _json.dumps(payload), ts),
        )
        c.commit()
        return int(cur.lastrowid)


def _recent_ts(seconds_ago: int = 0) -> str:
    """Return ISO-Z timestamp `seconds_ago` seconds before now."""
    from datetime import UTC, datetime, timedelta
    return (
        datetime.now(UTC) - timedelta(seconds=seconds_ago)
    ).isoformat().replace("+00:00", "Z")


def test_inference_tier1_kind_rule_match():
    from core.runtime.db import connect, _ensure_causal_edges_table
    from core.services.causal_inference_daemon import run_inference_cycle
    with connect() as c:
        _ensure_causal_edges_table(c)
    import uuid as _uuid
    cid = f"t1_{_uuid.uuid4().hex[:8]}"
    parent = _insert_event_with_payload(
        "tool.invoked", {"tool_call_id": cid}, _recent_ts(120),
    )
    child = _insert_event_with_payload(
        "tool.completed", {"tool_call_id": cid}, _recent_ts(118),
    )
    stats = run_inference_cycle(since_minutes=10)
    assert stats["edges_created"] >= 1 or stats["edges_upgraded"] >= 0
    with connect() as c:
        rows = c.execute(
            "SELECT * FROM causal_edges WHERE child_event_id = ? AND parent_event_id = ?",
            (child, parent),
        ).fetchall()
    assert len(rows) == 1
    assert rows[0]["source"] == "inferred-kind"
    assert rows[0]["confidence"] == 0.9


def test_inference_tier2_shared_id_match():
    from core.runtime.db import connect, _ensure_causal_edges_table
    from core.services.causal_inference_daemon import run_inference_cycle
    with connect() as c:
        _ensure_causal_edges_table(c)
    import uuid as _uuid
    rid = f"run_{_uuid.uuid4().hex[:8]}"
    parent = _insert_event_with_payload(
        "decision.created",
        {"run_id": rid, "decision_id": f"d_{rid}"},
        _recent_ts(180),
    )
    child = _insert_event_with_payload(
        "memory.seed_triggered",
        {"run_id": rid},
        _recent_ts(150),
    )
    run_inference_cycle(since_minutes=10)
    with connect() as c:
        rows = c.execute(
            "SELECT * FROM causal_edges WHERE child_event_id = ? AND parent_event_id = ?",
            (child, parent),
        ).fetchall()
    assert len(rows) == 1
    assert rows[0]["source"] == "inferred-id"
    assert rows[0]["confidence"] == 0.8


def test_inference_tier3_temporal_only():
    from core.runtime.db import connect, _ensure_causal_edges_table
    from core.services.causal_inference_daemon import run_inference_cycle
    with connect() as c:
        _ensure_causal_edges_table(c)
    import uuid as _uuid
    sid = f"chat-{_uuid.uuid4().hex[:8]}"
    parent = _insert_event_with_payload(
        "channel.message_inbound",
        {"session_id": sid},
        _recent_ts(240),
    )
    child = _insert_event_with_payload(
        "self_review.completed",
        {"session_id": sid},
        _recent_ts(220),
    )
    run_inference_cycle(since_minutes=10)
    with connect() as c:
        rows = c.execute(
            "SELECT * FROM causal_edges WHERE child_event_id = ? AND parent_event_id = ?",
            (child, parent),
        ).fetchall()
    assert len(rows) == 1
    assert rows[0]["source"] == "inferred-temporal"
    assert rows[0]["confidence"] == 0.4


def test_inference_idempotent_no_dupes():
    from core.runtime.db import connect, _ensure_causal_edges_table
    from core.services.causal_inference_daemon import run_inference_cycle
    with connect() as c:
        _ensure_causal_edges_table(c)
    import uuid as _uuid
    cid = f"idem_{_uuid.uuid4().hex[:8]}"
    p = _insert_event_with_payload(
        "tool.invoked", {"tool_call_id": cid}, _recent_ts(300),
    )
    ch = _insert_event_with_payload(
        "tool.completed", {"tool_call_id": cid}, _recent_ts(298),
    )
    run_inference_cycle(since_minutes=10)
    run_inference_cycle(since_minutes=10)
    with connect() as c:
        row = c.execute(
            "SELECT COUNT(*) AS n FROM causal_edges "
            "WHERE child_event_id = ? AND parent_event_id = ?",
            (ch, p),
        ).fetchone()
    assert int(row["n"]) == 1


def test_inference_upgrades_confidence():
    from core.runtime.db import connect, _ensure_causal_edges_table
    from core.services.causal_inference_daemon import (
        _record_edge, _ensure_table_ready,
    )
    with connect() as c:
        _ensure_causal_edges_table(c)
    import uuid as _uuid
    cid = f"upgrade_{_uuid.uuid4().hex[:8]}"
    p = _insert_event_with_payload(
        "tool.invoked", {"tool_call_id": cid}, _recent_ts(360),
    )
    ch = _insert_event_with_payload(
        "tool.completed", {"tool_call_id": cid}, _recent_ts(358),
    )
    _ensure_table_ready()
    _record_edge(child=ch, parent=p, edge_kind="triggered",
                 confidence=0.4, source="inferred-temporal",
                 reasoning="initial-low")
    _record_edge(child=ch, parent=p, edge_kind="triggered",
                 confidence=0.9, source="inferred-kind",
                 reasoning="upgraded")
    with connect() as c:
        row = c.execute(
            "SELECT confidence, source FROM causal_edges "
            "WHERE child_event_id = ? AND parent_event_id = ?",
            (ch, p),
        ).fetchone()
    assert float(row["confidence"]) == 0.9
    assert row["source"] == "inferred-kind"
