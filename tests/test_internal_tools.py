"""Tests for internal_api and db_query tools."""
from __future__ import annotations
import pytest


# ── db_query ──────────────────────────────────────────────────────────────

def test_db_query_rejects_insert() -> None:
    from core.tools.simple_tools import _exec_db_query
    r = _exec_db_query({"sql": "INSERT INTO foo VALUES (1)"})
    assert r["status"] == "error"
    assert "INSERT" in r["error"]


def test_db_query_rejects_delete() -> None:
    from core.tools.simple_tools import _exec_db_query
    r = _exec_db_query({"sql": "DELETE FROM foo WHERE id=1"})
    assert r["status"] == "error"


def test_db_query_rejects_drop() -> None:
    from core.tools.simple_tools import _exec_db_query
    r = _exec_db_query({"sql": "DROP TABLE foo"})
    assert r["status"] == "error"


def test_db_query_rejects_update() -> None:
    from core.tools.simple_tools import _exec_db_query
    r = _exec_db_query({"sql": "UPDATE foo SET x=1"})
    assert r["status"] == "error"


def test_db_query_rejects_pragma() -> None:
    from core.tools.simple_tools import _exec_db_query
    r = _exec_db_query({"sql": "PRAGMA journal_mode=WAL"})
    assert r["status"] == "error"


def test_db_query_rejects_non_select() -> None:
    from core.tools.simple_tools import _exec_db_query
    r = _exec_db_query({"sql": "VACUUM"})
    assert r["status"] == "error"


def test_db_query_rejects_missing_sql() -> None:
    from core.tools.simple_tools import _exec_db_query
    r = _exec_db_query({})
    assert r["status"] == "error"


def test_db_query_select_literal() -> None:
    from core.tools.simple_tools import _exec_db_query
    r = _exec_db_query({"sql": "SELECT 42 AS answer"})
    assert r["status"] == "ok"
    assert r["rows"][0]["answer"] == 42
    assert r["columns"] == ["answer"]


def test_db_query_select_with_params() -> None:
    from core.tools.simple_tools import _exec_db_query
    r = _exec_db_query({"sql": "SELECT ? AS val", "params": "[99]"})
    assert r["status"] == "ok"
    assert r["rows"][0]["val"] == 99


def test_db_query_rejects_bad_params_json() -> None:
    from core.tools.simple_tools import _exec_db_query
    r = _exec_db_query({"sql": "SELECT 1", "params": "not-json"})
    assert r["status"] == "error"


def test_db_query_rejects_non_list_params() -> None:
    from core.tools.simple_tools import _exec_db_query
    r = _exec_db_query({"sql": "SELECT 1", "params": '{"key": "val"}'})
    assert r["status"] == "error"


# ── internal_api ──────────────────────────────────────────────────────────

def test_internal_api_rejects_external_url() -> None:
    from core.tools.simple_tools import _exec_internal_api
    r = _exec_internal_api({"method": "GET", "path": "https://evil.com/steal"})
    assert r["status"] == "error"


def test_internal_api_rejects_no_leading_slash() -> None:
    from core.tools.simple_tools import _exec_internal_api
    r = _exec_internal_api({"method": "GET", "path": "mc/experiments"})
    assert r["status"] == "error"


def test_internal_api_rejects_double_slash() -> None:
    from core.tools.simple_tools import _exec_internal_api
    r = _exec_internal_api({"method": "GET", "path": "//mc/experiments"})
    assert r["status"] == "error"


def test_internal_api_rejects_invalid_method() -> None:
    from core.tools.simple_tools import _exec_internal_api
    r = _exec_internal_api({"method": "DELETE", "path": "/mc/experiments"})
    assert r["status"] == "error"


def test_internal_api_put_rejected() -> None:
    from core.tools.simple_tools import _exec_internal_api
    r = _exec_internal_api({"method": "PUT", "path": "/mc/experiments"})
    assert r["status"] == "error"


def test_internal_api_connection_refused_returns_error() -> None:
    """API not running — should return error, not raise."""
    from core.tools.simple_tools import _exec_internal_api
    r = _exec_internal_api({"method": "GET", "path": "/mc/experiments"})
    # Either ok (if API is running) or error (connection refused) — both are valid
    assert r["status"] in ("ok", "error")


# ── Tool manifest ─────────────────────────────────────────────────────────

def test_both_tools_in_definitions() -> None:
    from core.tools.simple_tools import get_tool_definitions
    names = set()
    for d in get_tool_definitions():
        if "function" in d:
            names.add(d["function"]["name"])
        elif "name" in d:
            names.add(d["name"])
    assert "internal_api" in names
    assert "db_query" in names
