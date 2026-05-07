"""Verify counterfactuals table created with UNIQUE(cf_key) constraint."""
import sqlite3
import pytest

from core.runtime.db import _ensure_counterfactuals_table


def test_table_created():
    conn = sqlite3.connect(":memory:")
    _ensure_counterfactuals_table(conn)
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='counterfactuals'"
    ).fetchone()
    assert row is not None


def test_table_has_expected_columns():
    conn = sqlite3.connect(":memory:")
    _ensure_counterfactuals_table(conn)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(counterfactuals)").fetchall()}
    expected = {
        "cf_id", "cf_key", "workspace_id", "cluster_id",
        "trigger_event_ids_json", "trigger_types_json",
        "what_if", "likely_difference", "reasoning",
        "llm_confidence", "apophenia_score", "final_confidence",
        "status", "created_at", "updated_at",
    }
    assert expected.issubset(cols), f"missing: {expected - cols}"


def test_cf_key_is_unique():
    conn = sqlite3.connect(":memory:")
    _ensure_counterfactuals_table(conn)
    conn.execute(
        "INSERT INTO counterfactuals(cf_id, cf_key, workspace_id, cluster_id, "
        "trigger_event_ids_json, trigger_types_json, what_if, status, created_at, updated_at) "
        "VALUES ('cf-1', 'key-A', 'default', 'c1', '[1]', '[\"x\"]', 'what if', "
        "'generated', 'now', 'now')"
    )
    # Second insert with same cf_key must fail
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO counterfactuals(cf_id, cf_key, workspace_id, cluster_id, "
            "trigger_event_ids_json, trigger_types_json, what_if, status, created_at, updated_at) "
            "VALUES ('cf-2', 'key-A', 'default', 'c2', '[2]', '[\"y\"]', 'what if', "
            "'generated', 'now', 'now')"
        )


def test_insert_or_ignore_is_idempotent():
    conn = sqlite3.connect(":memory:")
    _ensure_counterfactuals_table(conn)
    sql = (
        "INSERT OR IGNORE INTO counterfactuals(cf_id, cf_key, workspace_id, cluster_id, "
        "trigger_event_ids_json, trigger_types_json, what_if, status, created_at, updated_at) "
        "VALUES (?, ?, 'default', 'c1', '[1]', '[\"x\"]', 'what if', "
        "'generated', 'now', 'now')"
    )
    conn.execute(sql, ("cf-1", "key-A"))
    conn.execute(sql, ("cf-2", "key-A"))  # should be no-op
    rows = conn.execute("SELECT cf_id FROM counterfactuals").fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "cf-1"


def test_indexes_created():
    conn = sqlite3.connect(":memory:")
    _ensure_counterfactuals_table(conn)
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' "
        "AND name LIKE 'idx_counterfactuals_%'"
    ).fetchall()
    names = {r[0] for r in rows}
    assert "idx_counterfactuals_workspace_created" in names
    assert "idx_counterfactuals_status" in names


def test_idempotent_migration():
    conn = sqlite3.connect(":memory:")
    _ensure_counterfactuals_table(conn)
    _ensure_counterfactuals_table(conn)  # second run must not raise
