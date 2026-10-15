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


# ── Run-konteksten paa deny-stien (15/10-2026) ───────────────────────────
#
# Maalt: 468 denies for Michelles bruger stod med `run=-` og tom session_id.
# Aarsagen var et forkert NOEGLENAVN: stien laeste `_runtime_run_id`, men
# `simple_tool_executor._prepare_call` stamper `_runtime_turn_id`. Uden
# konteksten kan ét loebende run og 300 uafhaengige forsoeg ikke skelnes —
# og det var praecis spoergsmaalet der ikke kunne besvares.


def _fang_deny(monkeypatch) -> dict:
    """Fanger kaldet til `note_unauthorized` i stedet for at skrive i DB'en."""
    fanget: dict = {}

    def _fake(uid, sid, resource, reason, *, role="", run_id=""):
        fanget.update(uid=uid, sid=sid, resource=resource, reason=reason,
                      role=role, run_id=run_id)

    monkeypatch.setattr("core.services.connections.note_unauthorized", _fake)
    return fanget


def test_deny_baerer_run_og_session_fra_argumenterne(monkeypatch):
    """Executorens noegler skal naa helt frem til incident'en."""
    c = {"n": 0}
    monkeypatch.setitem(st._TOOL_HANDLERS, "bash", _dummy(c))
    _ctx(monkeypatch, "member", "chat")
    fanget = _fang_deny(monkeypatch)

    res = st.execute_tool("bash", {
        "command": "ls",
        "_runtime_turn_id": "visible-abc123",
        "_runtime_session_id": "chat-42",
    })

    assert res.get("error") == "tool_not_permitted"
    assert fanget["run_id"] == "visible-abc123", fanget
    assert fanget["sid"] == "chat-42", fanget


def test_deny_falder_tilbage_paa_koerslens_egen_kontekst(monkeypatch):
    """Uden `_runtime_*` i argumenterne skal koerslen selv spoerges.

    Det er den vej der virker for et vaerktoejskald hvis argumenter ikke bar
    konteksten — og den eneste der goer saadanne denies maalbare.
    """
    from core.services import run_autonomy_context as rac
    from core.identity import workspace_context as ws

    c = {"n": 0}
    monkeypatch.setitem(st._TOOL_HANDLERS, "bash", _dummy(c))
    _ctx(monkeypatch, "member", "chat")
    fanget = _fang_deny(monkeypatch)

    rac.set_run_identity("visible-kontekst-9", "wakeup")
    tok_sid = ws.set_session_id("chat-99")
    try:
        res = st.execute_tool("bash", {"command": "ls"})
    finally:
        rac.set_run_identity("", "")
        ws._current_state.reset(tok_sid)

    assert res.get("error") == "tool_not_permitted"
    assert fanget["run_id"] == "visible-kontekst-9", fanget
    assert fanget["sid"] == "chat-99", fanget
