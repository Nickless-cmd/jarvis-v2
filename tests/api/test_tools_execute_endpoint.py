from fastapi.testclient import TestClient
from apps.api.jarvis_api.app import app

client = TestClient(app)


def test_catalog_locked_returns_companions_and_load_more():
    r = client.get("/v1/tools/catalog", params={"unlocked": "false"})
    assert r.status_code == 200
    names = {(d.get("function") or d)["name"] for d in r.json()["tools"]}
    assert "remember_this" in names
    assert "load_more_tools" in names
    assert "runtime_bash" not in names


def test_catalog_unlocked_returns_runtime_aliases():
    r = client.get("/v1/tools/catalog", params={"unlocked": "true"})
    assert r.status_code == 200
    names = {(d.get("function") or d)["name"] for d in r.json()["tools"]}
    assert "runtime_bash" in names


def test_execute_unaliases_and_runs(monkeypatch):
    calls = {}
    def _fake_execute_tool(name, arguments):
        calls["name"] = name
        calls["arguments"] = arguments
        return {"status": "ok", "echo": arguments}
    monkeypatch.setattr(
        "apps.api.jarvis_api.routes.agent_loop.execute_tool", _fake_execute_tool
    )
    r = client.post("/v1/tools/execute",
                    json={"name": "runtime_bash", "arguments": {"command": "ls"}})
    assert r.status_code == 200
    assert calls["name"] == "bash"
    assert r.json()["result"]["status"] == "ok"


def test_execute_forwards_companion_untouched(monkeypatch):
    calls = {}
    monkeypatch.setattr(
        "apps.api.jarvis_api.routes.agent_loop.execute_tool",
        lambda name, arguments: calls.setdefault("name", name) or {"ok": True},
    )
    r = client.post("/v1/tools/execute",
                    json={"name": "search_memory", "arguments": {"query": "x"}})
    assert r.status_code == 200
    assert calls["name"] == "search_memory"


def test_execute_brain_write_denied_for_non_owner(monkeypatch):
    monkeypatch.setattr(
        "apps.api.jarvis_api.routes.agent_loop._resolve_role", lambda *a, **k: "member"
    )
    monkeypatch.setattr(
        "apps.api.jarvis_api.routes.agent_loop.execute_tool",
        lambda name, arguments: (_ for _ in ()).throw(AssertionError("should not run")),
    )
    r = client.post("/v1/tools/execute",
                    json={"name": "remember_this", "arguments": {"content": "x"}})
    assert r.status_code == 403
    assert "brain" in r.json()["detail"].lower()


def test_execute_runs_inside_workspace_context(monkeypatch):
    """Sanity: execute_tool sees the workspace ContextVar set by user_context —
    i.e. the context is entered on the SAME thread that runs the tool."""
    seen = {}
    def _fake_execute_tool(name, arguments):
        from core.identity.workspace_context import current_workspace_name
        seen["workspace"] = current_workspace_name()
        return {"ok": True}
    monkeypatch.setattr(
        "apps.api.jarvis_api.routes.agent_loop.execute_tool", _fake_execute_tool
    )
    r = client.post("/v1/tools/execute",
                    json={"name": "search_memory", "arguments": {"query": "x"}})
    assert r.status_code == 200
    # Owner default (empty user_id) resolves to Bjørn's default workspace.
    assert seen["workspace"] == "bjorn"
