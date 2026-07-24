from __future__ import annotations

import sqlite3

from core.runtime import db as runtime_db
import core.runtime.db_core as db_core


def test_connection_pool_reconnects_on_db_path_change(monkeypatch, tmp_path) -> None:
    # Regression (2026-07-24): the thread-local connection pool must not reuse a
    # connection after DB_PATH is repointed. Tests repoint DB_PATH per-test; a stale
    # pooled conn to a PRIOR db leaked state across tests ("no such table" / bled-over
    # rows) and was the root cause of ~70 full-suite failures.
    db_core.close_pooled_connection()
    a, b = tmp_path / "a.db", tmp_path / "b.db"
    monkeypatch.setattr(db_core, "DB_PATH", a)
    with runtime_db.connect() as conn:
        conn.execute("CREATE TABLE marker(x)")
        conn.commit()
    monkeypatch.setattr(db_core, "DB_PATH", b)
    with runtime_db.connect() as conn:
        names = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert "marker" not in names  # fresh DB b, not the stale pooled conn to a.db


def test_connect_context_manager_closes_connection(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "jarvis.db"
    monkeypatch.setattr(runtime_db, "DB_PATH", db_path)

    with runtime_db.connect() as conn:
        conn.execute("SELECT 1")

    try:
        conn.execute("SELECT 1")
    except sqlite3.ProgrammingError:
        pass
    else:
        raise AssertionError("runtime_db.connect() should close sqlite connection on context exit")
