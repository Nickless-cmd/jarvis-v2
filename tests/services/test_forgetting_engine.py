"""Tests for forgetting_engine — pure deletion logic."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    """Point core.runtime.db.DB_PATH at a fresh tmp file and init.

    Steers `connect()` at a fresh on-disk DB. All queries within one
    test see the same state. We also explicitly create
    cognitive_chronicle_entries and cognitive_personal_project_journal
    because these are not created by init_db() — they're lazily
    initialized by their respective modules in production.
    """
    db_path = tmp_path / "jarvis.db"
    from core.runtime import db as db_mod

    monkeypatch.setattr(db_mod, "DB_PATH", db_path)
    db_mod.init_db()

    # Create the episodic tables that init_db doesn't.
    with db_mod.connect() as conn:
        db_mod._ensure_cognitive_chronicle_entries_table(conn)
        # cognitive_personal_project_journal — minimal schema matching
        # the on-demand definition in core/services/personal_project.py.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cognitive_personal_project_journal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL,
                entry_text TEXT NOT NULL,
                source TEXT,
                mood_tone TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        # Re-run the soft_deleted_at migration now that both tables exist.
        db_mod._ensure_soft_deleted_at_columns(conn)
    return db_path


def test_period_label_recent_days(fresh_db):
    from core.services.forgetting_engine import compute_period_label
    now = datetime.now(UTC)
    released = now - timedelta(days=3)
    assert compute_period_label(released, now) == "~3 dage siden"


def test_period_label_weeks(fresh_db):
    from core.services.forgetting_engine import compute_period_label
    now = datetime.now(UTC)
    released = now - timedelta(days=14)
    assert compute_period_label(released, now) == "~2 uger siden"


def test_period_label_months(fresh_db):
    from core.services.forgetting_engine import compute_period_label
    now = datetime.now(UTC)
    released = now - timedelta(days=92)
    assert compute_period_label(released, now) == "~3 måneder siden"


def test_period_label_years(fresh_db):
    from core.services.forgetting_engine import compute_period_label
    now = datetime.now(UTC)
    released = now - timedelta(days=400)
    label = compute_period_label(released, now)
    assert "år siden" in label


def test_is_fredet_path_blocks_workspace_files(fresh_db):
    from core.services.forgetting_engine import is_fredet_path
    assert is_fredet_path("workspace/SOUL.md") is True
    assert is_fredet_path("workspace/USER.md") is True
    assert is_fredet_path("workspace/MEMORY.md") is True
    assert is_fredet_path("workspace/IDENTITY.md") is True
    assert is_fredet_path("workspace/CHRONICLE.md") is False  # not fredet


def test_is_fredet_table_blocks_self_model(fresh_db):
    from core.services.forgetting_engine import is_fredet_table
    assert is_fredet_table("cognitive_decisions") is True
    assert is_fredet_table("cognitive_self_model_state") is True
    assert is_fredet_table("concept_baseline_stats") is True
    assert is_fredet_table("absence_traces") is True
    assert is_fredet_table("cognitive_chronicle_entries") is False
    assert is_fredet_table("cognitive_personal_project_journal") is False


def test_release_memory_for_chronicle_entry(fresh_db):
    """Hard-deletes the row, inserts a self-marker, no content stored."""
    from core.runtime.db import connect
    from core.services.forgetting_engine import release_memory

    with connect() as conn:
        conn.execute(
            "INSERT INTO cognitive_chronicle_entries "
            "(entry_id, period, narrative, created_at, updated_at) "
            "VALUES ('e1', 'day-2026-02-01', 'private content', "
            "'2026-02-01T00:00:00Z', '2026-02-01T00:00:00Z')"
        )

    result = release_memory(
        memory_kind="chronicle_entry",
        memory_id="e1",
        workspace_id="default",
    )
    assert result["status"] == "released", result
    assert "period_label" in result

    # Row is gone
    with connect() as conn:
        rows = conn.execute(
            "SELECT entry_id FROM cognitive_chronicle_entries WHERE entry_id='e1'"
        ).fetchall()
        assert rows == []

        # Marker exists, but stores NO reference to e1 or its content
        markers = conn.execute(
            "SELECT trace_id, period_label, released_at FROM absence_traces "
            "WHERE track_kind='self_marker'"
        ).fetchall()
        assert len(markers) == 1
        marker_str = " ".join(str(c or "") for c in markers[0])
        assert "e1" not in marker_str
        assert "private content" not in marker_str


def test_release_memory_blocks_unknown_kind(fresh_db):
    """release_memory rejects unknown memory_kind values."""
    from core.services.forgetting_engine import release_memory
    result = release_memory(
        memory_kind="cognitive_decisions",  # not in the valid kind list
        memory_id="anything",
        workspace_id="default",
    )
    assert result["status"] == "rejected"


def test_release_memory_marker_recursive(fresh_db):
    """memory_kind='absence_marker' marks a self-marker as is_self_released."""
    from core.runtime.db_absence_traces import insert_self_marker, list_self_markers
    from core.services.forgetting_engine import release_memory

    m = insert_self_marker(workspace_id="default", period_label="~30 dage siden")
    result = release_memory(
        memory_kind="absence_marker",
        memory_id=m["trace_id"],
        workspace_id="default",
    )
    assert result["status"] == "released", result
    visible = list_self_markers(workspace_id="default")
    assert len(visible) == 0  # is_self_released=1 hides it


def test_release_memory_returns_period_label_from_created_at(fresh_db):
    """period_label must be computed from the row's created_at, not now."""
    from core.runtime.db import connect
    from core.services.forgetting_engine import release_memory
    old_date = (datetime.now(UTC) - timedelta(days=92)).isoformat().replace("+00:00", "Z")
    with connect() as conn:
        conn.execute(
            "INSERT INTO cognitive_chronicle_entries "
            "(entry_id, period, narrative, created_at, updated_at) "
            "VALUES ('old', 'day-old', 'x', ?, ?)",
            (old_date, old_date),
        )
    result = release_memory(
        memory_kind="chronicle_entry", memory_id="old", workspace_id="default"
    )
    assert "måneder siden" in result["period_label"], result


def test_release_memory_not_found(fresh_db):
    from core.services.forgetting_engine import release_memory
    result = release_memory(
        memory_kind="chronicle_entry",
        memory_id="does-not-exist",
        workspace_id="default",
    )
    assert result["status"] == "not_found"


def test_run_auto_cycle_soft_deletes_old_entries(fresh_db, monkeypatch):
    """Daemon cycle marks old entries soft-deleted and increments counter."""
    from core.runtime.db import connect
    from core.runtime.db_absence_traces import get_auto_counter
    from core.services.forgetting_engine import run_auto_cycle

    # Seed three old entries (older than min_age_days default 30)
    old = (datetime.now(UTC) - timedelta(days=60)).isoformat().replace("+00:00", "Z")
    with connect() as conn:
        for i in range(3):
            conn.execute(
                "INSERT INTO cognitive_chronicle_entries "
                "(entry_id, period, narrative, created_at, updated_at) "
                "VALUES (?, 'day-old', 'x', ?, ?)",
                (f"old-{i}", old, old),
            )

    result = run_auto_cycle(workspace_id="default")
    assert result["soft_deleted"] == 3, result

    # All 3 are soft-deleted
    with connect() as conn:
        live = conn.execute(
            "SELECT COUNT(*) FROM cognitive_chronicle_entries "
            "WHERE soft_deleted_at IS NULL"
        ).fetchone()[0]
        assert live == 0

    # Counter == 3
    counter = get_auto_counter(workspace_id="default")
    assert counter is not None
    assert counter["auto_count"] == 3


def test_run_auto_cycle_skips_recent_entries(fresh_db):
    from core.runtime.db import connect
    from core.services.forgetting_engine import run_auto_cycle

    young = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    with connect() as conn:
        conn.execute(
            "INSERT INTO cognitive_chronicle_entries "
            "(entry_id, period, narrative, created_at, updated_at) "
            "VALUES ('young', 'day-now', 'x', ?, ?)",
            (young, young),
        )

    result = run_auto_cycle(workspace_id="default")
    assert result["soft_deleted"] == 0


def test_run_auto_cycle_disabled_short_circuits(fresh_db, monkeypatch):
    from core.services.forgetting_engine import run_auto_cycle

    class _FakeSettings:
        forgetting_enabled = False
        forgetting_auto_decay_threshold = 0.95
        forgetting_auto_min_age_days = 30
        forgetting_auto_max_per_cycle = 200
        forgetting_grace_days = 7

    # Patch the load_settings reference inside the engine module —
    # since the engine imports load_settings at module load time, patching
    # core.runtime.settings.load_settings doesn't reach the engine's local ref.
    monkeypatch.setattr(
        "core.services.forgetting_engine.load_settings",
        lambda: _FakeSettings(),
    )
    result = run_auto_cycle(workspace_id="default")
    assert result["skipped"] == "disabled"


def test_run_auto_cycle_grace_sweep_hard_deletes_expired(fresh_db):
    from core.runtime.db import connect
    from core.services.forgetting_engine import run_auto_cycle

    # Seed a row that has been soft-deleted for 10 days (past grace=7)
    long_ago = (datetime.now(UTC) - timedelta(days=10)).isoformat().replace("+00:00", "Z")
    with connect() as conn:
        conn.execute(
            "INSERT INTO cognitive_chronicle_entries "
            "(entry_id, period, narrative, created_at, updated_at, soft_deleted_at) "
            "VALUES ('expired', 'day-old', 'x', ?, ?, ?)",
            (long_ago, long_ago, long_ago),
        )

    result = run_auto_cycle(workspace_id="default")
    assert result["hard_deleted"] >= 1

    # Row is physically gone
    with connect() as conn:
        rows = conn.execute(
            "SELECT entry_id FROM cognitive_chronicle_entries WHERE entry_id='expired'"
        ).fetchall()
        assert rows == []
