from __future__ import annotations

import sqlite3

from core.runtime import db as runtime_db


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
