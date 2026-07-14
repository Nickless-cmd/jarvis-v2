"""Fase 6 Task 5 — multi-user scoping regression on /v1/agent/step.

Guards the §8 migration BLOCKER (identity/memory/quota leak): the client-owned
agent lane must resolve identity/workspace/role from the AUTHENTICATED caller,
not hardcode Bjørn's `name="default"` workspace/identity. End-to-end via
TestClient (not unit calls to the pure helpers already covered elsewhere) so
the ACTUAL route wiring — _resolve_role -> _apply_privilege_enforcement,
user_id -> _resolve_workspace_name -> _build_system_prompt/_full_context,
user_id -> record_cost — is what's proven, not just the helpers in isolation.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.jarvis_api.app import app
import apps.api.jarvis_api.routes.agent_loop as al

client = TestClient(app)


def _patch_chat(monkeypatch, *, capture: dict | None = None, text="ok"):
    monkeypatch.setattr(al, "_resolve_target", lambda: ("deepseek", "deepseek-v4-flash"))

    def _fake_chat(**kw):
        if capture is not None:
            capture["messages"] = kw.get("messages")
        return {"text": text, "tool_calls": [], "input_tokens": 3, "output_tokens": 2,
                "cost_usd": 0.001, "finish_reason": "stop"}
    monkeypatch.setattr(
        "core.services.cheap_provider_runtime_adapters._execute_openai_compatible_chat",
        _fake_chat)


def test_agent_step_resolves_caller_workspace_not_default(monkeypatch):
    monkeypatch.setattr(al, "_flag", lambda name, default=False: name == "jc_agent_user_scoping")
    monkeypatch.setattr(al, "_resolve_workspace_name",
                        lambda user_id: "ws_member_x" if user_id == "member_x" else "default")
    monkeypatch.setattr(al, "_identity_context",
                        lambda name="default": f"IDENTITY-MARKER[{name}]")
    captured: dict = {}
    _patch_chat(monkeypatch, capture=captured)

    client.post("/v1/agent/step",
               json={"messages": [{"role": "user", "content": "hej"}], "stream": False,
                     "user_id": "member_x", "context": "identity"})

    system_msg = next(m for m in captured["messages"] if m.get("role") == "system")
    prompt = system_msg["content"]
    assert "IDENTITY-MARKER[ws_member_x]" in prompt
    assert "IDENTITY-MARKER[default]" not in prompt
    # the generic coding-agent framing must not claim the caller is on
    # Bjørn's machine when scoped to a different caller's workspace.
    assert "Bjørns terminal" not in prompt


def test_agent_step_does_not_leak_owner_memory_to_other_user(monkeypatch):
    monkeypatch.setattr(al, "_flag", lambda name, default=False: name == "jc_agent_user_scoping")
    monkeypatch.setattr(al, "_resolve_workspace_name",
                        lambda user_id: "ws_carol" if user_id == "carol" else "default")
    al._FULL_CTX_CACHE.clear()

    def _fake_assembly(*, provider, model, user_message, name="default"):
        class _A:
            text = f"MEMORY-RECALL-FOR::{name}"
        return _A()
    monkeypatch.setattr("core.services.prompt_contract.build_visible_chat_prompt_assembly",
                        _fake_assembly)
    captured: dict = {}
    _patch_chat(monkeypatch, capture=captured)

    client.post("/v1/agent/step",
               json={"messages": [{"role": "user", "content": "hvad husker du om mig?"}],
                     "stream": False, "user_id": "carol", "context": "full"})

    system_msg = next(m for m in captured["messages"] if m.get("role") == "system")
    prompt = system_msg["content"]
    assert "MEMORY-RECALL-FOR::ws_carol" in prompt
    assert "MEMORY-RECALL-FOR::default" not in prompt
    assert "MEMORY-RECALL-FOR::bjorn" not in prompt


def test_record_cost_tagged_with_caller_user_id(monkeypatch):
    monkeypatch.setattr(al, "_flag", lambda name, default=False: name == "jc_agent_observability")
    _patch_chat(monkeypatch)
    rec: dict = {}
    monkeypatch.setattr(al, "record_cost", lambda **k: rec.update(k))

    client.post("/v1/agent/step",
               json={"messages": [{"role": "user", "content": "hej"}], "stream": False,
                     "user_id": "dana"})

    assert rec["user_id"] == "dana"
    assert rec["user_id"] != ""


def test_bypass_fullauto_is_owner_only(monkeypatch):
    monkeypatch.setattr(al, "_flag", lambda name, default=False: name == "jc_privilege_enforcement")
    monkeypatch.setattr(al, "_resolve_role", lambda: "guest")
    _patch_chat(monkeypatch)

    r = client.post("/v1/agent/step",
                    json={"messages": [{"role": "user", "content": "hej"}], "stream": False,
                          "approval_mode": "bypass"})

    assert r.status_code == 200
    body = r.json()
    assert body["effective_approval_mode"] == "ask"
    assert body["privilege_downgraded"] is True


def test_bypass_fullauto_unrestricted_for_owner(monkeypatch):
    monkeypatch.setattr(al, "_flag", lambda name, default=False: name == "jc_privilege_enforcement")
    monkeypatch.setattr(al, "_resolve_role", lambda: "owner")
    _patch_chat(monkeypatch)

    r = client.post("/v1/agent/step",
                    json={"messages": [{"role": "user", "content": "hej"}], "stream": False,
                          "approval_mode": "bypass"})

    assert r.status_code == 200
    body = r.json()
    assert body["effective_approval_mode"] == "bypass"
    assert "privilege_downgraded" not in body
