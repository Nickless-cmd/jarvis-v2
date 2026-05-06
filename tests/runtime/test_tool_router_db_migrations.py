"""Verify tool_router DB tables can be created."""
import sqlite3

from core.runtime.db import _ensure_tool_router_tables


def test_tool_router_decisions_table_created():
    conn = sqlite3.connect(":memory:")
    _ensure_tool_router_tables(conn)
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name='tool_router_decisions'"
    ).fetchone()
    assert row is not None


def test_tool_router_load_more_table_created():
    conn = sqlite3.connect(":memory:")
    _ensure_tool_router_tables(conn)
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name='tool_router_load_more'"
    ).fetchone()
    assert row is not None


def test_tool_router_indexes_created():
    conn = sqlite3.connect(":memory:")
    _ensure_tool_router_tables(conn)
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' "
        "AND name LIKE 'idx_tool_router_%'"
    ).fetchall()
    names = {r[0] for r in rows}
    assert "idx_tool_router_decisions_created_at" in names
    assert "idx_tool_router_load_more_created_at" in names


def test_tool_router_tables_idempotent():
    conn = sqlite3.connect(":memory:")
    _ensure_tool_router_tables(conn)
    _ensure_tool_router_tables(conn)  # Should not raise
