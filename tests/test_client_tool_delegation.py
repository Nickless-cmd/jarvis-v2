"""Fase 1: klient-tool-delegering — state + async poll (hermetisk, in-memory state)."""
import asyncio

import core.services.visible_runs_sections.client_tool_delegation as ctd
import core.services.visible_runs_sections.run_control_state as rcs


def _inmem(monkeypatch):
    store: dict = {}
    monkeypatch.setattr(rcs, "set_runtime_state_value", lambda k, v: store.__setitem__(k, v))
    monkeypatch.setattr(rcs, "get_runtime_state_value", lambda k, default=None: store.get(k, default))
    return store


def test_begin_sets_pending(monkeypatch):
    _inmem(monkeypatch)
    ctd.begin_client_tool("c1", tool_name="bash", arguments={"command": "ls"},
                          run_id="r1", session_id="s1")
    st = rcs._get_visible_client_tool_state("c1")
    assert st["status"] == "pending"
    assert st["tool_name"] == "bash"
    assert st["run_id"] == "r1"
    assert st["arguments"] == {"command": "ls"}


def test_resolve_flips_to_resolved(monkeypatch):
    _inmem(monkeypatch)
    ctd.begin_client_tool("c2", tool_name="bash", arguments=None, run_id="r", session_id="s")
    assert rcs.resolve_visible_client_tool("c2", "hello output") is True
    st = rcs._get_visible_client_tool_state("c2")
    assert st["status"] == "resolved"
    assert st["result_text"] == "hello output"


def test_resolve_unknown_returns_false(monkeypatch):
    _inmem(monkeypatch)
    assert rcs.resolve_visible_client_tool("nope", "x") is False


def test_resolve_twice_is_idempotent_false(monkeypatch):
    _inmem(monkeypatch)
    ctd.begin_client_tool("c3", tool_name="bash", arguments=None, run_id="r", session_id="s")
    assert rcs.resolve_visible_client_tool("c3", "a") is True
    assert rcs.resolve_visible_client_tool("c3", "b") is False  # ikke længere pending
    assert rcs._get_visible_client_tool_state("c3")["result_text"] == "a"


def test_await_returns_result_when_preresolved(monkeypatch):
    _inmem(monkeypatch)
    ctd.begin_client_tool("c4", tool_name="bash", arguments=None, run_id="r", session_id="s")
    rcs.resolve_visible_client_tool("c4", "done")
    assert asyncio.run(ctd.await_client_tool_result("c4", timeout_s=5.0)) == "done"


def test_await_times_out_and_marks_expired(monkeypatch):
    _inmem(monkeypatch)
    ctd.begin_client_tool("c5", tool_name="bash", arguments=None, run_id="r", session_id="s")
    assert asyncio.run(ctd.await_client_tool_result("c5", timeout_s=0.0)) is None
    assert rcs._get_visible_client_tool_state("c5")["status"] == "expired"


def test_await_returns_none_on_expired(monkeypatch):
    _inmem(monkeypatch)
    ctd.begin_client_tool("c6", tool_name="bash", arguments=None, run_id="r", session_id="s")
    st = rcs._get_visible_client_tool_state("c6")
    st["status"] = "expired"
    rcs._set_visible_client_tool_state("c6", st)
    assert asyncio.run(ctd.await_client_tool_result("c6", timeout_s=5.0)) is None


# --- endpoint POST /chat/runs/{run_id}/tool-result --------------------------


def test_endpoint_resolves_pending(monkeypatch):
    _inmem(monkeypatch)
    from apps.api.jarvis_api.routes import chat as chat_routes
    ctd.begin_client_tool("e1", tool_name="bash", arguments=None, run_id="r", session_id="s")
    resp = asyncio.run(chat_routes.chat_client_tool_result("r", {"call_id": "e1", "result": "ok-out"}))
    assert resp["resolved"] is True
    assert rcs._get_visible_client_tool_state("e1")["result_text"] == "ok-out"


def test_endpoint_404_for_unknown(monkeypatch):
    _inmem(monkeypatch)
    from apps.api.jarvis_api.routes import chat as chat_routes
    from fastapi import HTTPException
    try:
        asyncio.run(chat_routes.chat_client_tool_result("r", {"call_id": "ghost", "result": "x"}))
        assert False, "expected 404"
    except HTTPException as exc:
        assert exc.status_code == 404


def test_endpoint_400_for_missing_call_id(monkeypatch):
    _inmem(monkeypatch)
    from apps.api.jarvis_api.routes import chat as chat_routes
    from fastapi import HTTPException
    try:
        asyncio.run(chat_routes.chat_client_tool_result("r", {"result": "x"}))
        assert False, "expected 400"
    except HTTPException as exc:
        assert exc.status_code == 400
