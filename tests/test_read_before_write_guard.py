"""Read-before-write guard — operator-side new-file behavior.

Regression: the operator guard blocked creating a BRAND-NEW file because it
ignored file_exists and always demanded a prior read. You can't read what
doesn't exist (ENOENT), so the write deadlocked → the LLM bypassed the guard
via `bash cat >`. Fix: honor file_exists=False (guard) + probe existence on
the operator side before blocking (handler).
"""
from __future__ import annotations

from unittest.mock import patch

from core.services.read_before_write_guard import check_operator_read_before_write


# ── Guard-level ───────────────────────────────────────────────────────────

def test_new_file_allowed_without_prior_read():
    ok, reason = check_operator_read_before_write(
        "/home/bs/brand-new.md", session_id="s1", file_exists=False
    )
    assert ok is True
    assert reason is None


def test_existing_unread_blocked():
    ok, _ = check_operator_read_before_write(
        "/home/bs/existing.md", session_id="s1", file_exists=True
    )
    assert ok is False


def test_unknown_existence_unread_blocked_conservative():
    ok, _ = check_operator_read_before_write(
        "/home/bs/maybe.md", session_id="s1", file_exists=None
    )
    assert ok is False


# ── Handler-level (_exec_operator_write_file) ─────────────────────────────

def _list_dir_result(names):
    return {"status": "ok", "result": [{"name": n, "type": "file"} for n in names]}


def test_handler_allows_new_file(monkeypatch):
    """Parent dir lists no matching name → new file → write proceeds."""
    from core.tools import simple_tools as st

    calls = {"wrote": False}

    def fake_run_operator_async(coro_fn, *, tool_name, timeout_s=35.0):
        if tool_name == "operator_list_dir":
            return _list_dir_result(["other.md"])  # target NOT present
        if tool_name == "operator_write_file":
            calls["wrote"] = True
            return {"status": "ok", "result": {"written": True}}
        return {"status": "ok", "result": None}

    monkeypatch.setattr(st, "_run_operator_async", fake_run_operator_async)
    monkeypatch.setattr(st, "_operator_user_id", lambda args: "owner")
    # operator_write_file_async is imported lazily inside the handler; the
    # fake _run_operator_async never calls it, so no further patch needed.

    out = st._exec_operator_write_file(
        {"path": "/home/bs/vesc-open-client-spec.md", "content": "hello"}
    )
    assert calls["wrote"] is True
    assert out.get("status") == "ok"


def test_handler_blocks_existing_unread_file(monkeypatch):
    """Parent dir lists the target → existing + unread → guard blocks."""
    from core.tools import simple_tools as st

    def fake_run_operator_async(coro_fn, *, tool_name, timeout_s=35.0):
        if tool_name == "operator_list_dir":
            return _list_dir_result(["vesc-open-client-spec.md"])  # target present
        return {"status": "ok", "result": None}

    monkeypatch.setattr(st, "_run_operator_async", fake_run_operator_async)
    monkeypatch.setattr(st, "_operator_user_id", lambda args: "owner")

    out = st._exec_operator_write_file(
        {"path": "/home/bs/vesc-open-client-spec.md", "content": "hello"}
    )
    assert out.get("status") == "error"
    assert out.get("blocked_by") == "read_before_write_guard"


def test_handler_force_skips_guard(monkeypatch):
    """force=true bypasses the guard entirely (no existence probe needed)."""
    from core.tools import simple_tools as st

    seen = {"list_dir": False, "wrote": False}

    def fake_run_operator_async(coro_fn, *, tool_name, timeout_s=35.0):
        if tool_name == "operator_list_dir":
            seen["list_dir"] = True
            return _list_dir_result(["vesc-open-client-spec.md"])
        if tool_name == "operator_write_file":
            seen["wrote"] = True
            return {"status": "ok", "result": {"written": True}}
        return {"status": "ok", "result": None}

    monkeypatch.setattr(st, "_run_operator_async", fake_run_operator_async)
    monkeypatch.setattr(st, "_operator_user_id", lambda args: "owner")

    out = st._exec_operator_write_file(
        {"path": "/home/bs/vesc-open-client-spec.md", "content": "x", "force": True}
    )
    assert seen["wrote"] is True
    assert seen["list_dir"] is False  # force → no probe
    assert out.get("status") == "ok"
