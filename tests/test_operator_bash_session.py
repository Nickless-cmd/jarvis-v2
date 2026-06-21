"""Tests for operator_bash_session — server-emuleret persistent operator-shell."""
from __future__ import annotations

import core.tools.operator_bash_session as obs


def _mk_bridge(monkeypatch, captured: list):
    """Mock _exec_operator_bash så vi fanger den wrappede kommando + styrer svaret."""
    import core.tools.simple_tools as st

    def fake(args):
        captured.append(args)
        return {"status": "ok", "result": {
            "platform": "darwin", "shell": "bash",
            "stdout": "hello-output\n__OBS_CWD__:/Users/x/proj\n",
            "stderr": "", "exit_code": 0, "timed_out": False}}
    monkeypatch.setattr(st, "_exec_operator_bash", fake)


def test_open_returns_session_id():
    res = obs._exec_operator_bash_session_open({"_user_id": "u1"})
    assert res["status"] == "ok" and res["session_id"].startswith("opsess-")


def test_run_strips_marker_and_persists_cwd(monkeypatch):
    cap: list = []
    _mk_bridge(monkeypatch, cap)
    sid = obs._exec_operator_bash_session_open({"_user_id": "u1"})["session_id"]
    res = obs._exec_operator_bash_session_run({"session_id": sid, "command": "ls"})
    # markøren er fjernet fra det Jarvis ser:
    assert res["result"]["stdout"] == "hello-output"
    assert "__OBS_CWD__" not in res["result"]["stdout"]
    # cwd er persisteret på sessionen:
    with obs._LOCK:
        assert obs._SESSIONS[sid]["cwd"] == "/Users/x/proj"
    # næste run prepender cd til den gemte cwd:
    obs._exec_operator_bash_session_run({"session_id": sid, "command": "pwd"})
    assert "cd /Users/x/proj" in cap[-1]["command"]
    # env persisteres via operator-side .env-fil:
    assert ".jarvis_opsess_" in cap[-1]["command"] and "export -p" in cap[-1]["command"]


def test_run_unknown_session_errors():
    res = obs._exec_operator_bash_session_run({"session_id": "opsess-nope", "command": "ls"})
    assert res["status"] == "error" and "unknown session_id" in res["error"]


def test_close_drops_session(monkeypatch):
    _mk_bridge(monkeypatch, [])
    sid = obs._exec_operator_bash_session_open({"_user_id": "u1"})["session_id"]
    assert obs._exec_operator_bash_session_close({"session_id": sid})["closed"] is True
    with obs._LOCK:
        assert sid not in obs._SESSIONS


def test_registered_in_tool_handlers_and_scope():
    import core.tools.simple_tools as st
    from core.tools.tool_scoping import CODE_MODE_TOOLS_BASE
    for n in ("operator_bash_session_open", "operator_bash_session_run",
              "operator_bash_session_close", "operator_bash_session_list"):
        assert n in st._TOOL_HANDLERS
        assert n in CODE_MODE_TOOLS_BASE
