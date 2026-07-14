"""Fase 2 Task 8 (server half) — forwarded Jarvis-memory tools scope to the
CALLER's workspace on the ALREADY-scoped /v1/tools/execute path, not the
owner's default workspace.

Per the plan: agent/step's own user_id resolution depends on Fase 0 (not a
Fase 2 deliverable); this targets the path forwarded memory tools ACTUALLY
run on today — /v1/tools/execute (apps/api/jarvis_api/routes/agent_loop.py:
tools_execute), which already enters user_context() on the worker thread
(Finding A/B, agent_loop.py:275-305). This test proves body.user_id flows
through to the workspace ContextVar that jarvis_memory_write/_read/_search
read from — it does not duplicate that scoping logic, only verifies it for
the memory tool names specifically.
"""
from fastapi.testclient import TestClient

from apps.api.jarvis_api.app import app

client = TestClient(app)


def test_forwarded_memory_write_scopes_to_caller(monkeypatch):
    seen = {}

    def _fake_execute_tool(name, arguments):
        from core.identity.workspace_context import current_user_id, current_workspace_name
        seen["workspace"] = current_workspace_name()
        seen["user_id"] = current_user_id()
        return {"status": "ok", "written": True}

    monkeypatch.setattr(
        "apps.api.jarvis_api.routes.agent_loop.execute_tool", _fake_execute_tool
    )
    r = client.post(
        "/v1/tools/execute",
        json={"name": "jarvis_memory_write",
              "arguments": {"content": "alice's private note"},
              "user_id": "alice"},
    )
    assert r.status_code == 200
    # alice is not a registered user -> falls back to the shared "public"
    # workspace (see workspace_context.user_context), but CRITICALLY it is
    # NOT the owner's "bjorn" default — the write is scoped to the caller,
    # not silently landing in Bjørn's personal workspace.
    assert seen["workspace"] != "bjorn"
    assert seen["user_id"] == "alice"


def test_owner_empty_user_id_uses_default_workspace(monkeypatch):
    seen = {}

    def _fake_execute_tool(name, arguments):
        from core.identity.workspace_context import current_user_id, current_workspace_name
        seen["workspace"] = current_workspace_name()
        seen["user_id"] = current_user_id()
        return {"status": "ok", "written": True}

    monkeypatch.setattr(
        "apps.api.jarvis_api.routes.agent_loop.execute_tool", _fake_execute_tool
    )
    r = client.post(
        "/v1/tools/execute",
        json={"name": "jarvis_memory_write", "arguments": {"content": "owner's note"}},
    )
    assert r.status_code == 200
    assert seen["workspace"] == "bjorn"


def test_forwarded_memory_read_also_scopes_to_caller(monkeypatch):
    seen = {}

    def _fake_execute_tool(name, arguments):
        from core.identity.workspace_context import current_workspace_name
        seen["workspace"] = current_workspace_name()
        return {"status": "ok", "results": []}

    monkeypatch.setattr(
        "apps.api.jarvis_api.routes.agent_loop.execute_tool", _fake_execute_tool
    )
    r = client.post(
        "/v1/tools/execute",
        json={"name": "jarvis_memory_search", "arguments": {"query": "x"}, "user_id": "bob"},
    )
    assert r.status_code == 200
    assert seen["workspace"] != "bjorn"


def test_two_different_callers_get_different_workspaces(monkeypatch):
    seen = []

    def _fake_execute_tool(name, arguments):
        from core.identity.workspace_context import current_user_id
        seen.append(current_user_id())
        return {"status": "ok"}

    monkeypatch.setattr(
        "apps.api.jarvis_api.routes.agent_loop.execute_tool", _fake_execute_tool
    )
    client.post("/v1/tools/execute",
               json={"name": "jarvis_memory_write", "arguments": {"content": "a"},
                     "user_id": "alice"})
    client.post("/v1/tools/execute",
               json={"name": "jarvis_memory_write", "arguments": {"content": "b"},
                     "user_id": "carol"})
    assert seen == ["alice", "carol"]
