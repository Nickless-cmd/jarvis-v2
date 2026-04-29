from unittest.mock import patch, MagicMock

from core.tools.claude_dispatch.tool import (
    _exec_dispatch_to_claude_code, _exec_dispatch_status,
)


def test_exec_dispatch_validates_spec_errors_with_status_error(tmp_dispatch_db):
    result = _exec_dispatch_to_claude_code({"goal": ""})
    assert result["status"] == "error"
    assert "goal" in result["error"]


def test_exec_dispatch_calls_runner_on_valid_spec(tmp_dispatch_db):
    with patch("core.tools.claude_dispatch.tool.run_dispatch") as mr, \
         patch("core.tools.claude_dispatch.tool._eventbus") as mb:
        mr.return_value = {"task_id": "abc", "status": "ok",
                           "tokens": 10, "branch": "claude/abc",
                           "diff_summary": "", "error": None}
        mb.return_value = MagicMock()
        result = _exec_dispatch_to_claude_code({
            "goal": "test", "scope_files": ["a.py"],
            "allowed_tools": ["Read"],
        })
    assert result["status"] == "ok"
    assert result["task_id"] == "abc"


def test_exec_dispatch_status_reads_audit_row(tmp_dispatch_db):
    from core.tools.claude_dispatch.audit import start_audit_row
    from core.tools.claude_dispatch.spec import parse_spec
    spec = parse_spec({"goal": "x", "scope_files": ["a.py"], "allowed_tools": ["Read"]})
    start_audit_row("query-me", spec)
    result = _exec_dispatch_status({"task_id": "query-me"})
    assert result["status"] == "ok"
    assert result["row"]["task_id"] == "query-me"


def test_exec_dispatch_status_missing(tmp_dispatch_db):
    result = _exec_dispatch_status({"task_id": "ghost"})
    assert result["status"] == "error"
    assert "not found" in result["error"]
