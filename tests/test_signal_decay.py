"""Tests for signal decay — archive and delete stale signals."""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _memory_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn


def _create_signal_table(conn: sqlite3.Connection, table: str) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL UNIQUE,
            signal_type TEXT NOT NULL DEFAULT '',
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )


def _insert_signal(
    conn: sqlite3.Connection,
    table: str,
    signal_id: str,
    status: str = "active",
    updated_at: str | None = None,
) -> None:
    now = datetime.now(UTC).isoformat()
    conn.execute(
        f"INSERT INTO {table} (signal_id, signal_type, status, title, summary, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (signal_id, "test", status, f"title-{signal_id}", f"summary-{signal_id}", now, updated_at or now),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# signal_archive table
# ---------------------------------------------------------------------------


class TestSignalArchiveTable:
    def test_ensure_creates_table(self) -> None:
        from core.runtime.db import _ensure_signal_archive_table

        conn = _memory_conn()
        _ensure_signal_archive_table(conn)
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='signal_archive'").fetchall()
        assert len(rows) == 1

    def test_ensure_idempotent(self) -> None:
        from core.runtime.db import _ensure_signal_archive_table

        conn = _memory_conn()
        _ensure_signal_archive_table(conn)
        _ensure_signal_archive_table(conn)  # should not raise


# ---------------------------------------------------------------------------
# signal_decay_archive_and_delete
# ---------------------------------------------------------------------------


class TestSignalDecayArchiveAndDelete:
    def test_archives_stale_signals_older_than_threshold(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from core.runtime import db as db_mod

        conn = _memory_conn()
        table = "runtime_goal_signals"
        _create_signal_table(conn, table)
        db_mod._ensure_signal_archive_table(conn)

        old_time = (datetime.now(UTC) - timedelta(hours=48)).isoformat()
        _insert_signal(conn, table, "sig-old-1", status="stale", updated_at=old_time)
        _insert_signal(conn, table, "sig-old-2", status="stale", updated_at=old_time)
        _insert_signal(conn, table, "sig-active", status="active", updated_at=old_time)

        # Monkeypatch connect to return our in-memory conn
        from contextlib import contextmanager

        @contextmanager
        def fake_connect():
            yield conn

        monkeypatch.setattr(db_mod, "connect", fake_connect)
        monkeypatch.setattr(db_mod, "_SIGNAL_TABLES_WITH_STATUS", [table])

        result = db_mod.signal_decay_archive_and_delete(stale_hours=24)

        assert result["archived"] == 2
        assert result["per_table"][table] == 2

        # Stale signals should be gone from source
        remaining = conn.execute(f"SELECT * FROM {table}").fetchall()
        assert len(remaining) == 1
        assert remaining[0]["signal_id"] == "sig-active"

        # Archive should have the deleted signals
        archived = conn.execute("SELECT * FROM signal_archive").fetchall()
        assert len(archived) == 2
        ids = {r["signal_id"] for r in archived}
        assert ids == {"sig-old-1", "sig-old-2"}
        assert archived[0]["source_table"] == table

    def test_ignores_recently_stale_signals(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from core.runtime import db as db_mod

        conn = _memory_conn()
        table = "runtime_goal_signals"
        _create_signal_table(conn, table)
        db_mod._ensure_signal_archive_table(conn)

        recent_time = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        _insert_signal(conn, table, "sig-recent", status="stale", updated_at=recent_time)

        from contextlib import contextmanager

        @contextmanager
        def fake_connect():
            yield conn

        monkeypatch.setattr(db_mod, "connect", fake_connect)
        monkeypatch.setattr(db_mod, "_SIGNAL_TABLES_WITH_STATUS", [table])

        result = db_mod.signal_decay_archive_and_delete(stale_hours=24)
        assert result["archived"] == 0

        remaining = conn.execute(f"SELECT * FROM {table}").fetchall()
        assert len(remaining) == 1

    def test_handles_missing_table_gracefully(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from core.runtime import db as db_mod

        conn = _memory_conn()
        db_mod._ensure_signal_archive_table(conn)

        from contextlib import contextmanager

        @contextmanager
        def fake_connect():
            yield conn

        monkeypatch.setattr(db_mod, "connect", fake_connect)
        monkeypatch.setattr(db_mod, "_SIGNAL_TABLES_WITH_STATUS", ["nonexistent_table"])

        result = db_mod.signal_decay_archive_and_delete(stale_hours=24)
        assert result["archived"] == 0
        assert result["tables_scanned"] == 1

    def test_multiple_tables(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from core.runtime import db as db_mod

        conn = _memory_conn()
        tables = ["runtime_goal_signals", "runtime_awareness_signals"]
        for t in tables:
            _create_signal_table(conn, t)
        db_mod._ensure_signal_archive_table(conn)

        old_time = (datetime.now(UTC) - timedelta(hours=48)).isoformat()
        _insert_signal(conn, tables[0], "g-1", status="stale", updated_at=old_time)
        _insert_signal(conn, tables[1], "a-1", status="stale", updated_at=old_time)
        _insert_signal(conn, tables[1], "a-2", status="stale", updated_at=old_time)

        from contextlib import contextmanager

        @contextmanager
        def fake_connect():
            yield conn

        monkeypatch.setattr(db_mod, "connect", fake_connect)
        monkeypatch.setattr(db_mod, "_SIGNAL_TABLES_WITH_STATUS", tables)

        result = db_mod.signal_decay_archive_and_delete(stale_hours=24)
        assert result["archived"] == 3
        assert result["per_table"]["runtime_goal_signals"] == 1
        assert result["per_table"]["runtime_awareness_signals"] == 2


# ---------------------------------------------------------------------------
# signal_archive_cleanup
# ---------------------------------------------------------------------------


class TestSignalArchiveCleanup:
    def test_removes_old_archives(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from core.runtime import db as db_mod

        conn = _memory_conn()
        db_mod._ensure_signal_archive_table(conn)

        old_archive = (datetime.now(UTC) - timedelta(days=60)).isoformat()
        recent_archive = (datetime.now(UTC) - timedelta(days=5)).isoformat()
        conn.execute(
            "INSERT INTO signal_archive (source_table, signal_id, archived_at) VALUES (?, ?, ?)",
            ("test_table", "old-sig", old_archive),
        )
        conn.execute(
            "INSERT INTO signal_archive (source_table, signal_id, archived_at) VALUES (?, ?, ?)",
            ("test_table", "recent-sig", recent_archive),
        )
        conn.commit()

        from contextlib import contextmanager

        @contextmanager
        def fake_connect():
            yield conn

        monkeypatch.setattr(db_mod, "connect", fake_connect)

        deleted = db_mod.signal_archive_cleanup(max_age_days=30)
        assert deleted == 1

        remaining = conn.execute("SELECT * FROM signal_archive").fetchall()
        assert len(remaining) == 1
        assert remaining[0]["signal_id"] == "recent-sig"


# ---------------------------------------------------------------------------
# signal_archive_recent
# ---------------------------------------------------------------------------


class TestSignalArchiveRecent:
    def test_returns_recent_entries(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from core.runtime import db as db_mod

        conn = _memory_conn()
        db_mod._ensure_signal_archive_table(conn)

        now = datetime.now(UTC).isoformat()
        for i in range(5):
            conn.execute(
                "INSERT INTO signal_archive (source_table, signal_id, signal_type, archived_at) VALUES (?, ?, ?, ?)",
                ("test_table", f"sig-{i}", "test", now),
            )
        conn.commit()

        from contextlib import contextmanager

        @contextmanager
        def fake_connect():
            yield conn

        monkeypatch.setattr(db_mod, "connect", fake_connect)

        results = db_mod.signal_archive_recent(limit=3)
        assert len(results) == 3
        assert "signal_id" in results[0]
        assert "source_table" in results[0]


# ---------------------------------------------------------------------------
# signal_decay_daemon
# ---------------------------------------------------------------------------


class TestSignalDecayDaemon:
    def test_tick_respects_cadence(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import apps.api.jarvis_api.services.signal_decay_daemon as sdd

        # Reset module state
        sdd._last_tick_at = datetime.now(UTC)
        sdd._last_result = {}

        result = sdd.tick_signal_decay_daemon()
        assert result["generated"] is False

    def test_tick_runs_on_first_call(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import apps.api.jarvis_api.services.signal_decay_daemon as sdd

        sdd._last_tick_at = None
        sdd._last_result = {}

        monkeypatch.setattr(
            "core.runtime.db.signal_decay_archive_and_delete",
            lambda stale_hours=24: {"archived": 3, "tables_scanned": 35, "per_table": {"t": 3}},
        )
        monkeypatch.setattr(
            "core.runtime.db.signal_archive_cleanup",
            lambda max_age_days=30: 1,
        )

        result = sdd.tick_signal_decay_daemon()
        assert result["generated"] is True
        assert result["archived"] == 3
        assert result["archive_cleaned"] == 1

    def test_tick_handles_errors_gracefully(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import apps.api.jarvis_api.services.signal_decay_daemon as sdd

        sdd._last_tick_at = None
        sdd._last_result = {}

        def boom(**kw):
            raise RuntimeError("db exploded")

        monkeypatch.setattr("core.runtime.db.signal_decay_archive_and_delete", boom)

        result = sdd.tick_signal_decay_daemon()
        assert result["generated"] is False
        assert "error" in result


# ---------------------------------------------------------------------------
# SIGNAL_TABLES_WITH_STATUS completeness
# ---------------------------------------------------------------------------


class TestSignalTablesList:
    def test_all_tables_present(self) -> None:
        from core.runtime.db import _SIGNAL_TABLES_WITH_STATUS

        # Should have 35+ tables
        assert len(_SIGNAL_TABLES_WITH_STATUS) >= 35

    def test_all_tables_have_runtime_prefix(self) -> None:
        from core.runtime.db import _SIGNAL_TABLES_WITH_STATUS

        for table in _SIGNAL_TABLES_WITH_STATUS:
            assert table.startswith("runtime_"), f"Table {table} missing runtime_ prefix"
            assert table.endswith("_signals"), f"Table {table} missing _signals suffix"


# ---------------------------------------------------------------------------
# build_signal_decay_surface
# ---------------------------------------------------------------------------


class TestBuildSignalDecaySurface:
    def test_returns_expected_keys(self) -> None:
        from apps.api.jarvis_api.services.signal_decay_daemon import build_signal_decay_surface

        surface = build_signal_decay_surface()
        assert "last_archived" in surface
        assert "last_archive_cleaned" in surface
        assert "tables_scanned" in surface
        assert "last_tick_at" in surface
