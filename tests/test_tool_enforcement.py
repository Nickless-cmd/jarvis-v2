"""Spor A — serverside tool-håndhævelse i execute_tool (defense-in-depth).

Selv hvis model-filteret omgås, skal execute_tool nægte uautoriserede kald for
non-owner-roller, mens owner og betroede interne (unbound) kald slipper igennem.
"""
from __future__ import annotations

import core.tools.simple_tools as st
import core.tools.tool_scoping as ts
import core.identity.workspace_context as wsctx
import core.services.workspace_trust as wt


def _ctx(monkeypatch, role, scope):
    monkeypatch.setattr(wsctx, "effective_role", lambda: role)
    monkeypatch.setattr(ts, "current_tool_scope", lambda: scope)
    monkeypatch.setattr(st, "_record_tool_outcome_memory", lambda *a, **k: None)
    monkeypatch.setattr(wt, "guard_code_write", lambda name: None)  # isolér trust-gaten


def _dummy(counter):
    def _h(args):
        counter["n"] += 1
        return {"status": "ok", "result": "ran"}
    return _h


def test_member_denied_disallowed_tool(monkeypatch):
    c = {"n": 0}
    monkeypatch.setitem(st._TOOL_HANDLERS, "bash", _dummy(c))
    _ctx(monkeypatch, "member", "chat")
    res = st.execute_tool("bash", {"command": "rm -rf /"})
    assert res.get("error") == "tool_not_permitted"
    assert res.get("role") == "member" and res.get("tool") == "bash"
    assert c["n"] == 0  # handler kørte ALDRIG


def test_member_allowed_tool_runs(monkeypatch):
    c = {"n": 0}
    monkeypatch.setitem(st._TOOL_HANDLERS, "web_search", _dummy(c))
    _ctx(monkeypatch, "member", "chat")
    res = st.execute_tool("web_search", {"query": "hej"})
    assert res.get("status") == "ok"
    assert c["n"] == 1


def test_owner_bypasses_gate(monkeypatch):
    c = {"n": 0}
    monkeypatch.setitem(st._TOOL_HANDLERS, "bash", _dummy(c))
    _ctx(monkeypatch, "owner", "chat")
    res = st.execute_tool("bash", {"command": "ls"})
    assert res.get("error") != "tool_not_permitted"
    assert c["n"] == 1


def test_daemon_unbound_bypasses_gate(monkeypatch):
    c = {"n": 0}
    monkeypatch.setitem(st._TOOL_HANDLERS, "bash", _dummy(c))
    _ctx(monkeypatch, "", "")
    res = st.execute_tool("bash", {"command": "ls"})
    assert res.get("error") != "tool_not_permitted"
    assert c["n"] == 1
