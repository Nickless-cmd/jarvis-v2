"""_ensure_users_table: DDL + PRAGMA koerte ved HVERT users-opslag (13 % af API-CPU maalt 14/11-2026).

Nu: skemaet sikres én gang pr. proces og DB-fil — som db_agent_contract._conn gor.
"""
from __future__ import annotations

import pytest


@pytest.fixture
def du(isolated_runtime, monkeypatch):
    import core.runtime.db_users as du_

    calls: list[str] = []
    real = du_._create_users_table
    monkeypatch.setattr(du_, "_create_users_table", lambda conn: (calls.append("ddl"), real(conn))[1])
    du_._USERS_ENSURED.clear()
    du_.calls_ = calls
    return du_


def _tables(conn) -> set[str]:
    return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}


def test_repeated_lookups_create_the_schema_once(du):
    for _ in range(5):
        assert du.get_user_row("ukendt") is None
    assert du.calls_ == ["ddl"]


def test_every_entry_point_shares_the_single_ensure(du):
    du.get_user_row("a")
    du.get_user_row_by_google_email_hash("h")
    du.get_user_row_by_email_hash("e")
    du.get_user_row_by_workspace("w")
    du.list_user_rows()
    assert du.calls_ == ["ddl"]


def test_the_users_table_really_exists_after_the_first_lookup(du):
    from core.runtime.db import connect

    du.get_user_row("a")
    with connect() as conn:
        assert "users" in _tables(conn)
        cols = {r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
    assert {"language", "google_email_hash"} <= cols


def test_a_different_database_file_is_ensured_again(du, tmp_path, monkeypatch):
    from core.runtime import db_core

    du.get_user_row("a")
    monkeypatch.setattr(db_core, "DB_PATH", tmp_path / "anden.db")
    du.get_user_row("a")
    assert du.calls_ == ["ddl", "ddl"]


def test_direct_ensure_on_a_connection_still_creates_and_migrates(isolated_runtime):
    """db_schema kalder _ensure_users_table(conn) direkte og skal stadig faa en komplet tabel."""
    import sqlite3

    import core.runtime.db_users as du_

    du_._USERS_ENSURED.clear()
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    du_._create_users_table(conn)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
    assert {"user_id", "language", "google_email_hash"} <= cols


def test_a_failed_ensure_is_retried_on_the_next_lookup(du, monkeypatch):
    """En laast DB under foerste forsoeg maa ikke efterlade 'sikret' uden en tabel."""
    import sqlite3

    state = {"n": 0}
    inner = du._create_users_table

    def flaky(conn):
        state["n"] += 1
        if state["n"] == 1:
            raise sqlite3.OperationalError("database is locked")
        return inner(conn)

    monkeypatch.setattr(du, "_create_users_table", flaky)
    with pytest.raises(sqlite3.OperationalError):
        du.get_user_row("a")
    assert du.get_user_row("a") is None
    assert state["n"] == 2
