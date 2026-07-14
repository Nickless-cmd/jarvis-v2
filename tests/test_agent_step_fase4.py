"""jarvis-code Fase 4 parity — SERVER side (apps/api/jarvis_api/routes/agent_loop.py).

Accumulates tests for Tasks 1, 2, 4, 7 of the Fase 4 parity plan. Every behavior
here is gated behind a NEW RuntimeSettings boolean (core/runtime/settings.py),
each defaulting to False — with the flag off, /v1/agent/step must behave
byte-identically to pre-Fase-4 code. Follows the monkeypatch-seam pattern from
tests/api/test_agent_step_envelope.py (module-level names on `agent_loop` are
the patch points; the chat-execution function is patched at its fully-qualified
origin since agent_loop imports it lazily inside the handler).

Task 1 (reasoning replay): monkeypatch al._settings for the flag, and
core.services.cheap_provider_runtime_adapters._execute_openai_compatible_chat
for the fake model response.
"""
from types import SimpleNamespace

from fastapi.testclient import TestClient

from apps.api.jarvis_api.app import app
import apps.api.jarvis_api.routes.agent_loop as al

client = TestClient(app)


def _fake_settings(**overrides) -> SimpleNamespace:
    """All four Fase-4 flags default False; override the ones under test.
    Mirrors _settings()'s real shape but avoids touching the on-disk config
    file — tests stay hermetic."""
    base = dict(
        agent_step_reasoning_replay_enabled=False,
        agent_step_env_block_enabled=False,
        agent_step_cache_contract_enabled=False,
        agent_step_harness_contract_enabled=False,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


# ── Task 1: extended-thinking / reasoning-replay across tool rounds ────────

def test_reasoning_forwarded_when_flag_on(monkeypatch):
    monkeypatch.setattr(al, "_resolve_target", lambda: ("deepseek", "deepseek-v4-flash"))
    monkeypatch.setattr(al, "_settings",
                        lambda: _fake_settings(agent_step_reasoning_replay_enabled=True))

    def _fake_chat(**kw):
        return {
            "text": "svar", "tool_calls": [{"id": "1", "type": "function",
                     "function": {"name": "bash", "arguments": "{}"}}],
            "input_tokens": 5, "output_tokens": 3, "cost_usd": 0.0,
            "finish_reason": "tool_calls", "reasoning_content": "because X",
        }
    monkeypatch.setattr(
        "core.services.cheap_provider_runtime_adapters._execute_openai_compatible_chat",
        _fake_chat)

    r = client.post("/v1/agent/step",
                    json={"messages": [{"role": "user", "content": "hej"}], "stream": False})
    assert r.status_code == 200
    assert r.json()["reasoning_content"] == "because X"


def test_reasoning_absent_when_flag_off(monkeypatch):
    monkeypatch.setattr(al, "_resolve_target", lambda: ("deepseek", "deepseek-v4-flash"))
    # flag defaults OFF -> don't monkeypatch al._settings at all (proves the REAL
    # default, not just a stubbed one, is inert).

    def _fake_chat(**kw):
        return {"text": "svar", "tool_calls": [], "input_tokens": 5, "output_tokens": 3,
                "cost_usd": 0.0, "finish_reason": "stop", "reasoning_content": "because X"}
    monkeypatch.setattr(
        "core.services.cheap_provider_runtime_adapters._execute_openai_compatible_chat",
        _fake_chat)

    r = client.post("/v1/agent/step",
                    json={"messages": [{"role": "user", "content": "hej"}], "stream": False})
    assert r.status_code == 200
    assert "reasoning_content" not in r.json()


def test_reasoning_stripped_for_non_deepseek_replay(monkeypatch):
    # Note (deviation): the route force-swaps any provider NOT in
    # _OPENAI_COMPATIBLE_PROVIDERS to deepseek before this point, so "ollama"
    # itself is unreachable here. "opencode" (IS openai-compatible, IS NOT
    # deepseek) stands in for the "ollama/copilot-compat style" class the plan
    # describes — the normalization rule is binary: retain for deepseek only.
    monkeypatch.setattr(al, "_settings",
                        lambda: _fake_settings(agent_step_reasoning_replay_enabled=True))
    captured = {}

    def _fake_chat(**kw):
        captured["messages"] = kw["messages"]
        return {"text": "ok", "tool_calls": [], "input_tokens": 1, "output_tokens": 1,
                "cost_usd": 0.0, "finish_reason": "stop"}
    monkeypatch.setattr(
        "core.services.cheap_provider_runtime_adapters._execute_openai_compatible_chat",
        _fake_chat)

    payload_messages = [
        {"role": "user", "content": "do X"},
        {"role": "assistant", "content": "", "reasoning_content": "thinking...",
         "tool_calls": [{"id": "1", "type": "function",
                         "function": {"name": "bash", "arguments": "{}"}}]},
        {"role": "tool", "tool_call_id": "1", "content": "result"},
    ]

    monkeypatch.setattr(al, "_resolve_target", lambda: ("opencode", "some-model"))
    client.post("/v1/agent/step", json={"messages": payload_messages, "stream": False})
    assistant_msg = [m for m in captured["messages"] if m.get("role") == "assistant"][-1]
    assert "reasoning_content" not in assistant_msg
    assert assistant_msg.get("tool_calls")  # tool_calls pairing preserved

    captured.clear()
    monkeypatch.setattr(al, "_resolve_target", lambda: ("deepseek", "deepseek-v4-flash"))
    client.post("/v1/agent/step", json={"messages": payload_messages, "stream": False})
    assistant_msg2 = [m for m in captured["messages"] if m.get("role") == "assistant"][-1]
    assert assistant_msg2.get("reasoning_content") == "thinking..."


def test_reasoning_forwarded_in_stream_done_when_flag_on(monkeypatch):
    monkeypatch.setattr(al, "_resolve_target", lambda: ("deepseek", "deepseek-v4-flash"))
    monkeypatch.setattr(al, "_settings",
                        lambda: _fake_settings(agent_step_reasoning_replay_enabled=True))

    def _fake_iter(**kw):
        yield {"kind": "delta", "text": "hej"}
        yield {"kind": "done", "full_text": "hej", "input_tokens": 3, "output_tokens": 2,
               "cost_usd": 0.0, "finish_reason": "stop", "reasoning_content": "fordi Y"}
    monkeypatch.setattr(
        "core.services.cheap_provider_runtime_streaming._iter_openai_compatible_chat_events",
        _fake_iter)
    with client.stream("POST", "/v1/agent/step",
                       json={"messages": [{"role": "user", "content": "hej"}], "stream": True}) as r:
        body = "".join(chunk for chunk in r.iter_text())
    import json as _j
    done = [ln for ln in body.splitlines() if ln.startswith("data:") and "reasoning_content" in ln][-1]
    payload = _j.loads(done[len("data: "):])
    assert payload["reasoning_content"] == "fordi Y"


def test_reasoning_absent_in_stream_done_when_flag_off(monkeypatch):
    monkeypatch.setattr(al, "_resolve_target", lambda: ("deepseek", "deepseek-v4-flash"))
    # flag OFF (default) — reasoning_content must not appear in the done payload.

    def _fake_iter(**kw):
        yield {"kind": "done", "full_text": "hej", "input_tokens": 1, "output_tokens": 1,
               "cost_usd": 0.0, "finish_reason": "stop", "reasoning_content": "fordi Y"}
    monkeypatch.setattr(
        "core.services.cheap_provider_runtime_streaming._iter_openai_compatible_chat_events",
        _fake_iter)
    with client.stream("POST", "/v1/agent/step",
                       json={"messages": [{"role": "user", "content": "hej"}], "stream": True}) as r:
        body = "".join(chunk for chunk in r.iter_text())
    import json as _j
    done = [ln for ln in body.splitlines() if ln.startswith("data:") and '"done"' not in ln][-1] \
        if False else [ln for ln in body.splitlines() if ln.startswith("data:")][-1]
    payload = _j.loads(done[len("data: "):])
    assert "reasoning_content" not in payload


def test_thinking_mode_threads_to_extra_body(monkeypatch):
    monkeypatch.setattr(al, "_resolve_target", lambda: ("deepseek", "deepseek-v4-flash"))
    monkeypatch.setattr(al, "_settings",
                        lambda: _fake_settings(agent_step_reasoning_replay_enabled=True))
    captured = {}

    def _fake_chat(**kw):
        captured["extra_body"] = kw.get("extra_body")
        captured["model"] = kw.get("model")
        return {"text": "ok", "tool_calls": [], "input_tokens": 1, "output_tokens": 1,
                "cost_usd": 0.0, "finish_reason": "stop"}
    monkeypatch.setattr(
        "core.services.cheap_provider_runtime_adapters._execute_openai_compatible_chat",
        _fake_chat)

    client.post("/v1/agent/step",
                json={"messages": [{"role": "user", "content": "hej"}], "stream": False,
                      "thinking_mode": "deep"})
    assert captured["extra_body"] == {"reasoning_effort": "max", "thinking": {"type": "enabled"}}


def test_thinking_mode_ignored_when_flag_off(monkeypatch):
    monkeypatch.setattr(al, "_resolve_target", lambda: ("deepseek", "deepseek-v4-flash"))
    captured = {}

    def _fake_chat(**kw):
        captured["extra_body"] = kw.get("extra_body")
        return {"text": "ok", "tool_calls": [], "input_tokens": 1, "output_tokens": 1,
                "cost_usd": 0.0, "finish_reason": "stop"}
    monkeypatch.setattr(
        "core.services.cheap_provider_runtime_adapters._execute_openai_compatible_chat",
        _fake_chat)

    client.post("/v1/agent/step",
                json={"messages": [{"role": "user", "content": "hej"}], "stream": False,
                      "thinking_mode": "deep"})
    assert captured["extra_body"] is None


# ── Task 2: <env> block in the system prompt ────────────────────────────────

def test_env_block_injected_when_flag_on(monkeypatch):
    monkeypatch.setattr(al, "_resolve_target", lambda: ("deepseek", "deepseek-v4-flash"))
    monkeypatch.setattr(al, "_settings",
                        lambda: _fake_settings(agent_step_env_block_enabled=True))
    captured = {}

    def _fake_chat(**kw):
        captured["messages"] = kw["messages"]
        return {"text": "ok", "tool_calls": [], "input_tokens": 1, "output_tokens": 1,
                "cost_usd": 0.0, "finish_reason": "stop"}
    monkeypatch.setattr(
        "core.services.cheap_provider_runtime_adapters._execute_openai_compatible_chat",
        _fake_chat)

    client.post("/v1/agent/step",
                json={"messages": [{"role": "user", "content": "hej"}], "stream": False,
                      "env": {"cwd": "/home/bs/proj", "git_branch": "main"}})
    system_msg = [m for m in captured["messages"] if m.get("role") == "system"][0]
    assert "<env>" in system_msg["content"]
    assert "/home/bs/proj" in system_msg["content"]
    assert "main" in system_msg["content"]


def test_env_block_absent_when_flag_off(monkeypatch):
    monkeypatch.setattr(al, "_resolve_target", lambda: ("deepseek", "deepseek-v4-flash"))
    # flag OFF (default) — don't monkeypatch al._settings.
    captured = {}

    def _fake_chat(**kw):
        captured["messages"] = kw["messages"]
        return {"text": "ok", "tool_calls": [], "input_tokens": 1, "output_tokens": 1,
                "cost_usd": 0.0, "finish_reason": "stop"}
    monkeypatch.setattr(
        "core.services.cheap_provider_runtime_adapters._execute_openai_compatible_chat",
        _fake_chat)

    client.post("/v1/agent/step",
                json={"messages": [{"role": "user", "content": "hej"}], "stream": False,
                      "env": {"cwd": "/home/bs/proj", "git_branch": "main"}})
    system_msg = [m for m in captured["messages"] if m.get("role") == "system"][0]
    assert "<env>" not in system_msg["content"]


def test_env_block_key_order_stable():
    from apps.api.jarvis_api.routes.jc_env import render_env_block
    a = render_env_block({"git_branch": "main", "cwd": "/x", "os": "linux"})
    b = render_env_block({"os": "linux", "cwd": "/x", "git_branch": "main"})
    c = render_env_block({"cwd": "/x", "git_branch": "main", "os": "linux"})
    assert a == b == c and a != ""


# ── Task 4: prompt-caching contract — stable prefix + telemetry ────────────

def test_prefix_signature_stable_across_steps(monkeypatch):
    monkeypatch.setattr(al, "_resolve_target", lambda: ("deepseek", "deepseek-v4-flash"))
    monkeypatch.setattr(al, "_settings",
                        lambda: _fake_settings(agent_step_cache_contract_enabled=True))

    def _fake_chat(**kw):
        return {"text": "ok", "tool_calls": [], "input_tokens": 1, "output_tokens": 1,
                "cost_usd": 0.0, "finish_reason": "stop",
                "cache_hit_tokens": 10, "cache_miss_tokens": 5}
    monkeypatch.setattr(
        "core.services.cheap_provider_runtime_adapters._execute_openai_compatible_chat",
        _fake_chat)
    seen_shas = []
    def _fake_record(**kw):
        seen_shas.append(kw.get("prefix_sha"))
    monkeypatch.setattr("core.services.cache_telemetry.record_visible_cache", _fake_record)

    # SAME last user message, but the second call has extra prior turns
    # (a growing conversation) — the recorded prefix signature must not move.
    client.post("/v1/agent/step",
                json={"messages": [{"role": "user", "content": "hej"}], "stream": False})
    client.post("/v1/agent/step",
                json={"messages": [
                    {"role": "user", "content": "turn 1"},
                    {"role": "assistant", "content": "svar 1"},
                    {"role": "user", "content": "hej"},
                ], "stream": False})
    assert len(seen_shas) == 2
    assert seen_shas[0] == seen_shas[1]
    assert seen_shas[0]  # non-empty


def test_env_tail_does_not_bust_prefix(monkeypatch):
    monkeypatch.setattr(al, "_resolve_target", lambda: ("deepseek", "deepseek-v4-flash"))
    monkeypatch.setattr(al, "_settings",
                        lambda: _fake_settings(agent_step_cache_contract_enabled=True,
                                              agent_step_env_block_enabled=True))

    def _fake_chat(**kw):
        return {"text": "ok", "tool_calls": [], "input_tokens": 1, "output_tokens": 1,
                "cost_usd": 0.0, "finish_reason": "stop",
                "cache_hit_tokens": 1, "cache_miss_tokens": 1}
    monkeypatch.setattr(
        "core.services.cheap_provider_runtime_adapters._execute_openai_compatible_chat",
        _fake_chat)
    seen_shas = []
    def _fake_record(**kw):
        seen_shas.append(kw.get("prefix_sha"))
    monkeypatch.setattr("core.services.cache_telemetry.record_visible_cache", _fake_record)

    client.post("/v1/agent/step",
                json={"messages": [{"role": "user", "content": "hej"}], "stream": False,
                      "env": {"git_branch": "main"}})
    client.post("/v1/agent/step",
                json={"messages": [{"role": "user", "content": "hej"}], "stream": False,
                      "env": {"git_branch": "some-other-branch-entirely"}})
    assert len(seen_shas) == 2
    assert seen_shas[0] == seen_shas[1]


def test_cache_tokens_in_usage(monkeypatch):
    monkeypatch.setattr(al, "_resolve_target", lambda: ("deepseek", "deepseek-v4-flash"))
    monkeypatch.setattr(al, "_settings",
                        lambda: _fake_settings(agent_step_cache_contract_enabled=True))

    def _fake_chat(**kw):
        return {"text": "ok", "tool_calls": [], "input_tokens": 50, "output_tokens": 5,
                "cost_usd": 0.0, "finish_reason": "stop",
                "cache_hit_tokens": 100, "cache_miss_tokens": 20}
    monkeypatch.setattr(
        "core.services.cheap_provider_runtime_adapters._execute_openai_compatible_chat",
        _fake_chat)

    r = client.post("/v1/agent/step",
                    json={"messages": [{"role": "user", "content": "hej"}], "stream": False})
    usage = r.json()["usage"]
    assert usage["cache_hit_tokens"] == 100
    assert usage["cache_miss_tokens"] == 20


def test_cache_contract_off_no_new_usage_keys(monkeypatch):
    monkeypatch.setattr(al, "_resolve_target", lambda: ("deepseek", "deepseek-v4-flash"))
    # flag OFF (default)

    def _fake_chat(**kw):
        return {"text": "ok", "tool_calls": [], "input_tokens": 50, "output_tokens": 5,
                "cost_usd": 0.0, "finish_reason": "stop",
                "cache_hit_tokens": 100, "cache_miss_tokens": 20}
    monkeypatch.setattr(
        "core.services.cheap_provider_runtime_adapters._execute_openai_compatible_chat",
        _fake_chat)
    calls = []
    monkeypatch.setattr("core.services.cache_telemetry.record_visible_cache",
                        lambda **k: calls.append(k))

    r = client.post("/v1/agent/step",
                    json={"messages": [{"role": "user", "content": "hej"}], "stream": False})
    usage = r.json()["usage"]
    assert "cache_hit_tokens" not in usage
    assert calls == []
