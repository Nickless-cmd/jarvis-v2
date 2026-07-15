"""Tests for operator_session_* — owner-gated backup channel for jarvis-code.

Covers: open (bridge probe + session), run (dispatches via bridge with
skip_approval, flattens result), owner-gate (non-owner refused), bridge-down
(error not crash), and _TOOL_HANDLERS/scope registration.

Spec: docs/superpowers/specs/2026-07-14-operator-channel-design.md
"""
from __future__ import annotations

import core.tools.operator_tools as ot


def _mock_bridge(monkeypatch, *, ok=True, stdout="out\n", captured=None):
    """Patch simple_tools._exec_operator_bash (the skip_approval dispatch path)."""
    import core.tools.simple_tools as st

    def fake(args):
        if captured is not None:
            captured.append(args)
        if not ok:
            return {"status": "error", "error": "bridge_not_connected"}
        return {"status": "ok", "result": {
            "stdout": stdout, "stderr": "", "exit_code": 0,
            "timed_out": False, "approved": True}}

    monkeypatch.setattr(st, "_exec_operator_bash", fake)


def _as_owner(monkeypatch):
    """Force effective_role() -> 'owner' so the server-side owner-gate passes."""
    import core.identity.workspace_context as wc
    monkeypatch.setattr(wc, "effective_role", lambda: "owner")


def test_open_probes_bridge_and_returns_session(monkeypatch):
    _as_owner(monkeypatch)
    cap: list = []
    _mock_bridge(monkeypatch, ok=True, captured=cap)
    res = ot._exec_operator_session_open({"_user_id": "u1"})
    assert res["status"] == "ok"
    assert res["session_id"].startswith("opchan-")
    # liveness probe ran a no-op via the bridge
    assert cap and cap[0]["command"] == "true"


def test_open_bridge_down_errors(monkeypatch):
    _as_owner(monkeypatch)
    _mock_bridge(monkeypatch, ok=False)
    res = ot._exec_operator_session_open({"_user_id": "u1"})
    assert res["status"] == "error"
    assert "bridge_not_connected" in res["error"]


def test_run_dispatches_skip_approval_and_flattens(monkeypatch):
    _as_owner(monkeypatch)
    cap: list = []
    _mock_bridge(monkeypatch, ok=True, stdout="/media/projects\n", captured=cap)
    sid = ot._exec_operator_session_open({"_user_id": "u1"})["session_id"]
    cap.clear()
    res = ot._exec_operator_session_run(
        {"session_id": sid, "command": "ls /media/projects", "cwd": "/home/bs/jarvis-code"})
    assert res["status"] == "ok"
    # flattened bridge fields visible at top level
    assert res["stdout"] == "/media/projects\n"
    assert res["exit_code"] == 0
    assert res["session_id"] == sid
    # the command was forwarded verbatim, WITH the cwd
    assert cap[-1]["command"] == "ls /media/projects"
    assert cap[-1]["cwd"] == "/home/bs/jarvis-code"


def test_run_unknown_session_errors(monkeypatch):
    _as_owner(monkeypatch)
    _mock_bridge(monkeypatch, ok=True)
    res = ot._exec_operator_session_run({"session_id": "opchan-nope", "command": "ls"})
    assert res["status"] == "error"
    assert "unknown session_id" in res["error"]


def test_run_bridge_down_returns_error_not_crash(monkeypatch):
    _as_owner(monkeypatch)
    _mock_bridge(monkeypatch, ok=False)
    # no session_id → runs directly with resolved uid; bridge down → error
    res = ot._exec_operator_session_run({"command": "ls /media", "_user_id": "u1"})
    assert res["status"] == "error"
    assert "bridge_not_connected" in res["error"]


def test_run_requires_command(monkeypatch):
    _as_owner(monkeypatch)
    res = ot._exec_operator_session_run({"session_id": ""})
    assert res["status"] == "error" and "command is required" in res["error"]


def test_owner_gate_non_owner_refused(monkeypatch):
    import core.identity.workspace_context as wc
    monkeypatch.setattr(wc, "effective_role", lambda: "member")
    for fn, args in (
        (ot._exec_operator_session_open, {"_user_id": "m1"}),
        (ot._exec_operator_session_run, {"command": "ls", "_user_id": "m1"}),
        (ot._exec_operator_session_close, {"session_id": "x"}),
    ):
        res = fn(args)
        assert res["status"] == "error"
        assert "owner-only" in res["error"]


def test_close_drops_session(monkeypatch):
    _as_owner(monkeypatch)
    _mock_bridge(monkeypatch, ok=True)
    sid = ot._exec_operator_session_open({"_user_id": "u1"})["session_id"]
    assert ot._exec_operator_session_close({"session_id": sid})["closed"] is True
    with ot._OP_SESS_LOCK:
        assert sid not in ot._OPERATOR_SESSIONS


def test_registered_in_handlers_and_owner_scope():
    import core.tools.simple_tools as st
    from core.tools.tool_scoping import CODE_MODE_OWNER_EXTRA, CODE_MODE_TOOLS_BASE
    for n in ("operator_session_open", "operator_session_run", "operator_session_close"):
        assert n in st._TOOL_HANDLERS
        # owner-only: in the owner-extra scope, NOT in the member/guest base
        assert n in CODE_MODE_OWNER_EXTRA
        assert n not in CODE_MODE_TOOLS_BASE
