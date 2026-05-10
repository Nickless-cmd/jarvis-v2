"""Schema migration for user_temperature_active (Lag 10 Phase 1)."""
from __future__ import annotations

import sqlite3

import pytest

from core.runtime.db import _ensure_user_temperature_active_table


def test_table_created() -> None:
    conn = sqlite3.connect(":memory:")
    _ensure_user_temperature_active_table(conn)
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='user_temperature_active'"
    ).fetchone()
    assert row is not None


def test_table_has_expected_columns() -> None:
    conn = sqlite3.connect(":memory:")
    _ensure_user_temperature_active_table(conn)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(user_temperature_active)").fetchall()}
    expected = {
        "field_id", "workspace_id",
        "field_valens", "field_arousal", "field_texture",
        "field_intensity", "field_conflict",
        "struct_valens", "struct_arousal", "struct_texture",
        "struct_confidence", "struct_signals_json", "last_structural_at",
        "llm_valens", "llm_arousal", "llm_texture",
        "llm_confidence", "llm_rationale", "last_llm_at",
        "llm_trigger_pending",
        "baseline_message_count", "baseline_built_at", "baseline_stats_json",
        "created_at", "updated_at",
    }
    assert expected.issubset(cols), f"missing: {expected - cols}"


def test_workspace_id_is_unique() -> None:
    conn = sqlite3.connect(":memory:")
    _ensure_user_temperature_active_table(conn)
    conn.execute(
        "INSERT INTO user_temperature_active (field_id, workspace_id, last_structural_at, "
        "created_at, updated_at) VALUES ('a', 'default', 'now', 'now', 'now')"
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO user_temperature_active (field_id, workspace_id, last_structural_at, "
            "created_at, updated_at) VALUES ('b', 'default', 'now', 'now', 'now')"
        )


def test_table_creation_is_idempotent() -> None:
    conn = sqlite3.connect(":memory:")
    _ensure_user_temperature_active_table(conn)
    _ensure_user_temperature_active_table(conn)
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='user_temperature_active'"
    ).fetchone()
    assert row is not None
