"""Schema migration for dream_bias_active (Lag 2 Phase 1)."""
from __future__ import annotations

import sqlite3

import pytest

from core.runtime.db import _ensure_dream_bias_active_table


def test_dream_bias_active_table_created() -> None:
    conn = sqlite3.connect(":memory:")
    _ensure_dream_bias_active_table(conn)
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='dream_bias_active'"
    ).fetchone()
    assert row is not None


def test_dream_bias_active_has_expected_columns() -> None:
    conn = sqlite3.connect(":memory:")
    _ensure_dream_bias_active_table(conn)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(dream_bias_active)").fetchall()}
    expected = {
        "bias_id", "workspace_id",
        "attention_bias_json", "threshold_bias_json",
        "intensity", "ttl_expires_at",
        "dream_text", "accumulated_count", "last_dream_at",
        "source_event_ids_json", "source_kinds_json",
        "created_at", "updated_at",
    }
    assert expected.issubset(cols), f"missing: {expected - cols}"


def test_workspace_id_is_unique() -> None:
    conn = sqlite3.connect(":memory:")
    _ensure_dream_bias_active_table(conn)
    conn.execute(
        "INSERT INTO dream_bias_active (bias_id, workspace_id, ttl_expires_at, "
        "last_dream_at, created_at, updated_at) VALUES "
        "('a', 'default', 'ttl', 'now', 'now', 'now')"
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO dream_bias_active (bias_id, workspace_id, ttl_expires_at, "
            "last_dream_at, created_at, updated_at) VALUES "
            "('b', 'default', 'ttl', 'now', 'now', 'now')"
        )


def test_table_creation_is_idempotent() -> None:
    conn = sqlite3.connect(":memory:")
    _ensure_dream_bias_active_table(conn)
    _ensure_dream_bias_active_table(conn)  # must not raise
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='dream_bias_active'"
    ).fetchone()
    assert row is not None
