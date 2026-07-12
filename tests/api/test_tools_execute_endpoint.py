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


def test_execute_normalizes_name(monkeypatch):
    """Finding A: the SAME normalized name (unalias+strip+lower) must reach both the
    brain-write gate and execute_tool. A messy alias with surrounding whitespace/caps
    must still resolve to the canonical dispatch name."""
    calls = {}
    monkeypatch.setattr(
        "apps.api.jarvis_api.routes.agent_loop.execute_tool",
        lambda name, arguments: calls.setdefault("name", name) or {"ok": True},
    )
    r = client.post("/v1/tools/execute",
                    json={"name": "  RUNTIME_BASH  ", "arguments": {"command": "ls"}})
    assert r.status_code == 200
    assert calls["name"] == "bash"
    assert r.json()["name"] == "bash"


def test_execute_non_owner_role_reaches_tool_layer(monkeypatch):
    """Finding B: a non-owner caller's real role must be visible to execute_tool via the
    workspace ContextVar — NOT reset to "" (owner-equivalent). This proves the inner
    server-side auth gate (simple_tools:_execute_tool_impl) sees the true role."""
    monkeypatch.setattr(
        "apps.api.jarvis_api.routes.agent_loop._resolve_role", lambda *a, **k: "member"
    )
    seen = {}
    def _fake_execute_tool(name, arguments):
        from core.identity.workspace_context import effective_role
        seen["role"] = effective_role()
        return {"ok": True}
    monkeypatch.setattr(
        "apps.api.jarvis_api.routes.agent_loop.execute_tool", _fake_execute_tool
    )
    # search_memory is not a brain-write tool → passes the endpoint gate, so we reach
    # execute_tool and can observe the role the inner gate would enforce on.
    r = client.post("/v1/tools/execute",
                    json={"name": "search_memory", "arguments": {"query": "x"}})
    assert r.status_code == 200
    assert seen["role"] == "member", (
        "caller role must reach the tool layer; got %r (empty/owner = privilege escalation)"
        % seen.get("role")
    )


def test_execute_owner_role_preserved(monkeypatch):
    """Owner path must still resolve to full owner role at the tool layer (do not break owner)."""
    monkeypatch.setattr(
        "apps.api.jarvis_api.routes.agent_loop._resolve_role", lambda *a, **k: "owner"
    )
    seen = {}
    def _fake_execute_tool(name, arguments):
        from core.identity.workspace_context import effective_role
        seen["role"] = effective_role()
        return {"ok": True}
    monkeypatch.setattr(
        "apps.api.jarvis_api.routes.agent_loop.execute_tool", _fake_execute_tool
    )
    r = client.post("/v1/tools/execute",
                    json={"name": "search_memory", "arguments": {"query": "x"}})
    assert r.status_code == 200
    assert seen["role"] == "owner"


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


def test_execute_injects_session_and_turn_id_for_brain_tools(monkeypatch):
    captured = {}
    def _fake_execute_tool(name, arguments):
        captured["args"] = dict(arguments)
        return {"status": "ok", "written": True}
    monkeypatch.setattr(
        "apps.api.jarvis_api.routes.agent_loop.execute_tool", _fake_execute_tool
    )
    # owner by default -> brain gate allows
    r = client.post("/v1/tools/execute",
                    json={"name": "remember_this",
                          "arguments": {"kind": "insight", "title": "t", "content": "c",
                                        "visibility": "personal", "domain": "general"},
                          "session_id": "sess-1", "turn_id": "turn-9"})
    assert r.status_code == 200
    a = captured["args"]
    assert a.get("_runtime_session_id") == "sess-1"
    assert a.get("_runtime_turn_id") == "turn-9"


def test_execute_synthesizes_turn_id_when_absent(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        "apps.api.jarvis_api.routes.agent_loop.execute_tool",
        lambda name, arguments: captured.setdefault("args", dict(arguments)) or {"ok": True},
    )
    r = client.post("/v1/tools/execute",
                    json={"name": "remember_this",
                          "arguments": {"kind": "insight", "title": "t", "content": "c",
                                        "visibility": "personal", "domain": "general"},
                          "session_id": "sess-2"})  # no turn_id
    assert r.status_code == 200
    tid = captured["args"].get("_runtime_turn_id")
    assert tid and len(tid) > 0   # synthesized, non-empty
