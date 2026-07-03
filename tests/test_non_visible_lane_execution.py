"""Tests for non_visible_lane_execution — Axis 3 tools plumbing.

Covers the coverage-gate for non_visible_lane_execution and pins that
execute_with_role_or_fallback forwards a tools/messages payload to the
primary provider and surfaces tool_calls back to the caller — the wiring
that lets a sub-agent's allowed_tools actually reach the model.
"""
from __future__ import annotations

from core.services import non_visible_lane_execution as nvl


def test_flatten_and_estimate_helpers_present():
    # Sanity: module still exposes the entry point + estimator.
    assert callable(nvl.execute_with_role_or_fallback)
    assert nvl._estimate_tokens("a b c d") >= 1


def test_role_fallback_forwards_tools_and_returns_tool_calls(monkeypatch):
    captured = {}

    def _fake_chat(**kwargs):
        captured.update(kwargs)
        return {
            "text": "",
            "tool_calls": [{"id": "c1", "function": {"name": "read_file", "arguments": "{}"}}],
            "input_tokens": 7,
            "output_tokens": 0,
            "cost_usd": 0.0,
        }

    # Patch the lazily-imported provider chat + registry.
    import core.services.cheap_provider_runtime as cheap
    monkeypatch.setattr(cheap, "_execute_provider_chat", _fake_chat)
    monkeypatch.setattr(
        cheap, "provider_runtime_defaults", lambda p: {"base_url": "https://x"}
    )
    monkeypatch.setattr(
        cheap, "record_cheap_provider_invocation", lambda **k: None
    )
    import core.runtime.provider_router as pr
    monkeypatch.setattr(
        pr, "load_provider_router_registry",
        lambda: {"providers": [{"provider": "deepseek", "base_url": "https://x", "auth_profile": "ds"}]},
    )
    # Circuit breaker should not skip.
    import core.services.provider_circuit_breaker as cb
    monkeypatch.setattr(cb, "should_skip", lambda p, m: False, raising=False)
    monkeypatch.setattr(cb, "record_success", lambda p, m: None, raising=False)

    tools = [{"type": "function", "function": {"name": "read_file"}}]
    msgs = [{"role": "user", "content": "go"}]
    result = nvl.execute_with_role_or_fallback(
        provider="deepseek", model="m", messages=msgs, tools=tools, requires_tools=True,
    )
    # Tools + messages reached the provider call.
    assert captured["tools"] == tools
    assert captured["messages"] == msgs
    # message coerced to None when messages given.
    assert captured["message"] is None
    # tool_calls surfaced back to the caller.
    assert result["tool_calls"][0]["function"]["name"] == "read_file"
    assert result["execution_mode"] == "role-primary-direct"


def test_role_fallback_legacy_text_only_still_works(monkeypatch):
    def _fake_chat(**kwargs):
        # Legacy path: message given, no tools/messages.
        assert kwargs.get("tools") is None
        assert kwargs.get("messages") is None
        assert kwargs.get("message") == "plain prompt"
        return {"text": "hi", "tool_calls": [], "input_tokens": 3, "output_tokens": 2, "cost_usd": 0.0}

    import core.services.cheap_provider_runtime as cheap
    monkeypatch.setattr(cheap, "_execute_provider_chat", _fake_chat)
    monkeypatch.setattr(cheap, "provider_runtime_defaults", lambda p: {"base_url": "https://x"})
    monkeypatch.setattr(cheap, "record_cheap_provider_invocation", lambda **k: None)
    import core.runtime.provider_router as pr
    monkeypatch.setattr(
        pr, "load_provider_router_registry",
        lambda: {"providers": [{"provider": "deepseek", "base_url": "https://x", "auth_profile": "ds"}]},
    )
    import core.services.provider_circuit_breaker as cb
    monkeypatch.setattr(cb, "should_skip", lambda p, m: False, raising=False)
    monkeypatch.setattr(cb, "record_success", lambda p, m: None, raising=False)

    result = nvl.execute_with_role_or_fallback(
        message="plain prompt", provider="deepseek", model="m",
    )
    assert result["text"] == "hi"
    # Backward compat: tool_calls key present but empty.
    assert result["tool_calls"] == []
