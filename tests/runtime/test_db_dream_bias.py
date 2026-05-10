"""Tests for db_dream_bias helpers."""
from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    """Steer connect() at a fresh on-disk DB for each test."""
    db_path = tmp_path / "jarvis.db"
    from core.runtime import db as db_mod
    monkeypatch.setattr(db_mod, "DB_PATH", db_path)
    db_mod.init_db()
    return db_path


def test_insert_new_bias_creates_row(fresh_db):
    from core.runtime.db_dream_bias import insert_new_bias

    result = insert_new_bias(
        workspace_id="default",
        attention_bias={"unfinished_business": 0.4},
        threshold_bias={"loop_persistence": 0.2},
        intensity=0.6,
        ttl_hours=8,
        dream_text="test dream",
        source_event_ids=["e1", "e2"],
        source_kinds=["self_review_outcome"],
    )
    assert result["accumulated_count"] == 1
    assert result["intensity"] == 0.6


def test_get_active_bias_raw_returns_inserted(fresh_db):
    from core.runtime.db_dream_bias import insert_new_bias, get_active_bias_raw

    insert_new_bias(
        workspace_id="default",
        attention_bias={"regret_threads": 0.5},
        threshold_bias={},
        intensity=0.7,
        ttl_hours=8,
        dream_text="x",
        source_event_ids=[],
        source_kinds=[],
    )
    row = get_active_bias_raw(workspace_id="default")
    assert row is not None
    assert row["intensity"] == 0.7
    assert row["attention_bias"] == {"regret_threads": 0.5}


def test_get_active_bias_raw_returns_none_for_unknown_workspace(fresh_db):
    from core.runtime.db_dream_bias import get_active_bias_raw
    row = get_active_bias_raw(workspace_id="nonexistent")
    assert row is None


def test_update_existing_bias_replaces_values(fresh_db):
    from core.runtime.db_dream_bias import (
        insert_new_bias, update_existing_bias, get_active_bias_raw,
    )

    insert_new_bias(
        workspace_id="default",
        attention_bias={"unfinished_business": 0.3},
        threshold_bias={},
        intensity=0.5,
        ttl_hours=8,
        dream_text="first",
        source_event_ids=["e1"],
        source_kinds=["self_review_outcome"],
    )
    update_existing_bias(
        workspace_id="default",
        attention_bias={"unfinished_business": 0.6, "regret_threads": 0.4},
        threshold_bias={"loop_persistence": -0.2},
        intensity=0.8,
        ttl_hours=8,
        dream_text="first\n— second",
        accumulated_count=2,
        source_event_ids=["e1", "e2"],
        source_kinds=["self_review_outcome", "decision_revoked"],
    )
    row = get_active_bias_raw(workspace_id="default")
    assert row["accumulated_count"] == 2
    assert row["intensity"] == 0.8
    assert row["attention_bias"]["regret_threads"] == 0.4
    assert "second" in row["dream_text"]


def test_delete_expired_removes_old_rows(fresh_db):
    from datetime import datetime, timezone, timedelta
    from core.runtime.db import connect
    from core.runtime.db_dream_bias import (
        insert_new_bias, delete_expired_bias_rows,
    )

    insert_new_bias(
        workspace_id="default",
        attention_bias={},
        threshold_bias={},
        intensity=0.5,
        ttl_hours=8,
        dream_text="x",
        source_event_ids=[],
        source_kinds=[],
    )
    expired_iso = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    with connect() as c:
        c.execute(
            "UPDATE dream_bias_active SET ttl_expires_at = ? WHERE workspace_id = ?",
            (expired_iso, "default"),
        )

    deleted = delete_expired_bias_rows()
    assert deleted == 1

    with connect() as c:
        n = c.execute("SELECT COUNT(*) FROM dream_bias_active").fetchone()[0]
    assert n == 0
