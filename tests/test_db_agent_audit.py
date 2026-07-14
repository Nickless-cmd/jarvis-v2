"""Unit tests for core/runtime/db_agent_audit.py — the write_row/read_rows
DB layer for the Fase 5 Task 9 audit trail (self-safe: never raises, mirrors
core/runtime/db_gate_verdicts.py's connect()/_ensure_table pattern)."""
import sqlite3

import pytest

from core.runtime import db_agent_audit


class _FakeConn:
    def __init__(self):
        self._conn = sqlite3.connect(":memory:")
        self._conn.row_factory = sqlite3.Row

    def __enter__(self):
        return self._conn

    def __exit__(self, *a):
        return False


@pytest.fixture
def fake_db(monkeypatch):
    conn_holder = _FakeConn()
    monkeypatch.setattr(db_agent_audit, "connect", lambda: conn_holder)
    return conn_holder


def test_write_row_returns_true_on_success(fake_db):
    assert db_agent_audit.write_row(user_id="u1", role="owner", tool="bash",
                                    target_summary="ls", decision="allow") is True


def test_write_row_self_safe_on_connect_failure(monkeypatch):
    def _boom():
        raise RuntimeError("db down")
    monkeypatch.setattr(db_agent_audit, "connect", _boom)
    assert db_agent_audit.write_row(user_id="u1", role="owner", tool="bash") is False


def test_read_rows_most_recent_first(fake_db):
    db_agent_audit.write_row(user_id="u1", role="owner", tool="first", decision="allow")
    db_agent_audit.write_row(user_id="u1", role="owner", tool="second", decision="allow")
    rows = db_agent_audit.read_rows(user_id="u1")
    assert [r["tool"] for r in rows] == ["second", "first"]


def test_read_rows_filters_by_user(fake_db):
    db_agent_audit.write_row(user_id="u1", role="owner", tool="a", decision="allow")
    db_agent_audit.write_row(user_id="u2", role="guest", tool="b", decision="deny")
    rows = db_agent_audit.read_rows(user_id="u1")
    assert len(rows) == 1 and rows[0]["tool"] == "a"


def test_read_rows_no_filter_returns_all(fake_db):
    db_agent_audit.write_row(user_id="u1", role="owner", tool="a", decision="allow")
    db_agent_audit.write_row(user_id="u2", role="guest", tool="b", decision="deny")
    rows = db_agent_audit.read_rows()
    assert len(rows) == 2


def test_read_rows_limit_clamped(fake_db):
    for i in range(5):
        db_agent_audit.write_row(user_id="u1", role="owner", tool=f"t{i}", decision="allow")
    rows = db_agent_audit.read_rows(user_id="u1", limit=2)
    assert len(rows) == 2


def test_read_rows_self_safe_on_failure(monkeypatch):
    def _boom():
        raise RuntimeError("db down")
    monkeypatch.setattr(db_agent_audit, "connect", _boom)
    assert db_agent_audit.read_rows() == []


def test_row_shape_has_expected_columns(fake_db):
    db_agent_audit.write_row(user_id="u1", role="owner", tool="bash",
                             target_summary="ls -la", decision="allow")
    row = db_agent_audit.read_rows()[0]
    for key in ("id", "ts", "user_id", "role", "tool", "target_summary", "decision"):
        assert key in row
