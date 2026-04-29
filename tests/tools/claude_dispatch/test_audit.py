import json
import pytest

from core.tools.claude_dispatch.audit import (
    start_audit_row, finalize_audit_row, read_audit_row,
)
from core.tools.claude_dispatch.spec import parse_spec


def _spec():
    return parse_spec({
        "goal": "test", "scope_files": ["a.py"], "allowed_tools": ["Read"],
    })


def test_start_audit_row_creates_running_entry(tmp_dispatch_db):
    start_audit_row("task-1", _spec())
    row = read_audit_row("task-1")
    assert row["status"] == "running"
    assert row["task_id"] == "task-1"
    assert row["ended_at"] is None
    spec_loaded = json.loads(row["spec_json"])
    assert spec_loaded["goal"] == "test"


def test_finalize_audit_row_writes_terminal_fields(tmp_dispatch_db):
    start_audit_row("task-2", _spec())
    finalize_audit_row(
        "task-2", status="ok", tokens_used=1234,
        exit_code=0, diff_summary="2 files changed", error=None,
    )
    row = read_audit_row("task-2")
    assert row["status"] == "ok"
    assert row["tokens_used"] == 1234
    assert row["exit_code"] == 0
    assert row["diff_summary"] == "2 files changed"
    assert row["ended_at"] is not None


def test_read_audit_row_missing_returns_none(tmp_dispatch_db):
    assert read_audit_row("nope") is None
