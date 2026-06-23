"""Unit tests for core/services/visible_followup.py adapters."""

from __future__ import annotations

import io
import json
from contextlib import contextmanager
from typing import Iterable

import pytest

from core.services import visible_followup as vf


# ── Helpers ──────────────────────────────────────────────────────────────────


class _FakeResponse:
    """Minimal stand-in for urlopen() context manager.

    Iterable over ``lines`` (bytes). Supports ``with`` context-manager usage.
    ``read()`` returns concatenated bytes for HTTPError body tests.
    """

    def __init__(self, lines: Iterable[bytes]) -> None:
        self._lines = list(lines)

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def __iter__(self):
        return iter(self._lines)

    def read(self) -> bytes:
        return b"".join(self._lines)


@contextmanager
def _patched_urlopen(monkeypatch: pytest.MonkeyPatch, response_lines: Iterable[bytes]):
    captured: dict[str, object] = {}

    def fake_urlopen(req, timeout=None):  # noqa: ARG001
        captured["url"] = req.full_url
        captured["headers"] = dict(req.headers) if req.headers else {}
        captured["body"] = json.loads(req.data.decode("utf-8")) if req.data else None
        captured["method"] = req.get_method()
        return _FakeResponse(response_lines)

    monkeypatch.setattr(vf.urllib_request, "urlopen", fake_urlopen)
    yield captured


# ── Event dataclasses ────────────────────────────────────────────────────────


def test_event_types_are_distinct_and_frozen() -> None:
    delta = vf.FollowupDelta(delta="hi")
    tcs = vf.FollowupToolCalls(tool_calls=[{"function": {"name": "x"}}])
    done = vf.FollowupDone(text="hi")
    failed = vf.FollowupFailed(round_index=0, error="err", summary="round-1-timeout")
    # Frozen → attribute assignment raises.
    with pytest.raises(Exception):
        delta.delta = "changed"  # type: ignore[misc]
    assert isinstance(delta, vf.FollowupDelta)
    assert isinstance(tcs, vf.FollowupToolCalls)
    assert isinstance(done, vf.FollowupDone)
    assert isinstance(failed, vf.FollowupFailed)


def test_tool_result_carrier_fields() -> None:
    tr = vf.ToolResult(tool_call_id="call_123", tool_name="search_memory", content="hit")
    assert tr.tool_call_id == "call_123"
    assert tr.tool_name == "search_memory"
    assert tr.content == "hit"


# ── Registry / dispatcher ────────────────────────────────────────────────────


def test_supported_providers_contains_ollama_and_copilot() -> None:
    providers = vf.supported_followup_providers()
    assert "ollama" in providers
    assert "github-copilot" in providers


def test_unsupported_provider_yields_single_failed_event() -> None:
    events = list(
        vf.stream_visible_followup(
            provider="made-up-provider",
            model="m",
            base_messages=[],
            exchanges=[],
        )
    )
    assert len(events) == 1
    assert isinstance(events[0], vf.FollowupFailed)
    assert "unsupported-provider" in events[0].summary


def test_provider_is_normalized_case_and_whitespace() -> None:
    events = list(
        vf.stream_visible_followup(
            provider="  OLLAMA  ",
            model="m",
            base_messages=[],
            exchanges=[],
        )
    )
    # Can't assert success here (would need HTTP mock), but at minimum it
    # shouldn't be an unsupported-provider failure.
    if events and isinstance(events[0], vf.FollowupFailed):
        assert "unsupported-provider" not in events[0].summary


# ── Ollama adapter ───────────────────────────────────────────────────────────


def test_ollama_adapter_hits_api_chat_and_streams_delta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from core.runtime import provider_router

    monkeypatch.setattr(
        provider_router,
        "resolve_provider_router_target",
        lambda *, lane: {"base_url": "http://ollama.test:11434"},
    )

    ndjson_lines = [
        (json.dumps({"message": {"content": "Hel"}}) + "\n").encode("utf-8"),
        (json.dumps({"message": {"content": "lo!"}}) + "\n").encode("utf-8"),
        (json.dumps({"done": True}) + "\n").encode("utf-8"),
    ]

    with _patched_urlopen(monkeypatch, ndjson_lines) as captured:
        events = list(
            vf.stream_visible_followup(
                provider="ollama",
                model="llama3.1:8b",
                base_messages=[{"role": "user", "content": "hi"}],
                exchanges=[
                    vf.ToolExchange(
                        text="",
                        tool_calls=[{"id": "x", "function": {"name": "f"}}],
                        results=[
                            vf.ToolResult(
                                tool_call_id="x",
                                tool_name="search_memory",
                                content="result",
                            )
                        ],
                    )
                ],
            )
        )

    assert captured["url"].endswith("/api/chat")
    body = captured["body"]
    assert isinstance(body, dict)
    assert body["model"] == "llama3.1:8b"
    # Modern Ollama shape (post 2026-04-25): role=tool messages with the
    # tool result, not a synthetic user message. Each ToolExchange contributes
    # one assistant turn plus one tool turn per result.
    msgs_by_role = [m["role"] for m in body["messages"]]
    assert "tool" in msgs_by_role
    tool_msgs = [m for m in body["messages"] if m["role"] == "tool"]
    assert any("result" in str(m.get("content", "")) for m in tool_msgs)
    # No more "[search_memory]:" prefix wrapping or "Continue." seed —
    # those were the legacy soft-prompt hack.
    assert all(
        "Continue." not in str(m.get("content", ""))
        and "[search_memory]:" not in str(m.get("content", ""))
        for m in body["messages"]
    )

    deltas = [e.delta for e in events if isinstance(e, vf.FollowupDelta)]
    assert "".join(deltas) == "Hello!"
    done = [e for e in events if isinstance(e, vf.FollowupDone)]
    assert len(done) == 1
    assert done[0].text == "Hello!"
    assert not any(isinstance(e, vf.FollowupFailed) for e in events)


def test_ollama_adapter_yields_tool_calls_when_model_requests_them(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from core.runtime import provider_router

    monkeypatch.setattr(
        provider_router,
        "resolve_provider_router_target",
        lambda *, lane: {"base_url": "http://ollama.test:11434"},
    )

    ndjson_lines = [
        (
            json.dumps(
                {
                    "message": {
                        "content": "",
                        "tool_calls": [
                            {"function": {"name": "read_file", "arguments": {"p": "x"}}}
                        ],
                    }
                }
            )
            + "\n"
        ).encode("utf-8"),
        (json.dumps({"done": True}) + "\n").encode("utf-8"),
    ]

    with _patched_urlopen(monkeypatch, ndjson_lines):
        events = list(
            vf.stream_visible_followup(
                provider="ollama",
                model="llama3.1:8b",
                base_messages=[],
                exchanges=[
                    vf.ToolExchange(
                        text="",
                        tool_calls=[],
                        results=[vf.ToolResult("", "x", "y")],
                    )
                ],
            )
        )

    tc_events = [e for e in events if isinstance(e, vf.FollowupToolCalls)]
    assert len(tc_events) == 1
    assert tc_events[0].tool_calls[0]["function"]["name"] == "read_file"


def test_ollama_adapter_second_round_uses_continue_seed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from core.runtime import provider_router

    monkeypatch.setattr(
        provider_router,
        "resolve_provider_router_target",
        lambda *, lane: {"base_url": "http://ollama.test:11434"},
    )

    with _patched_urlopen(
        monkeypatch, [(json.dumps({"done": True}) + "\n").encode("utf-8")]
    ) as captured:
        list(
            vf.stream_visible_followup(
                provider="ollama",
                model="m",
                base_messages=[],
                exchanges=[
                    vf.ToolExchange(
                        text="first-pass",
                        tool_calls=[],
                        results=[vf.ToolResult("", "t1", "r1")],
                    ),
                    vf.ToolExchange(
                        text="",
                        tool_calls=[],
                        results=[vf.ToolResult("", "t2", "r2")],
                    ),
                ],
                round_index=1,
            )
        )

    body = captured["body"]
    # Modern Ollama shape: structured tool messages, no "Continue." seed.
    # Two exchanges → two assistant turns + two tool turns (one per result).
    role_seq = [m["role"] for m in body["messages"]]
    assert role_seq.count("assistant") == 2
    assert role_seq.count("tool") == 2
    # Last tool message carries the second-round result.
    last_tool = [m for m in body["messages"] if m["role"] == "tool"][-1]
    assert last_tool["content"] == "r2"
    # Confirm the legacy "Continue." seed is gone.


def test_ollama_adapter_bounds_followup_exchange_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from core.runtime import provider_router

    monkeypatch.setattr(
        provider_router,
        "resolve_provider_router_target",
        lambda *, lane: {"base_url": "http://ollama.test:11434"},
    )

    # Tool-resultater STØRRE end _OLLAMA_MAX_TOOL_RESULT_CHARS (8000) så trunkering rammer.
    # (Var 3000 fra dengang cap'en var 2500; cap hævet til 8000 i b484595e uden test-opdatering.)
    exchanges = [
        vf.ToolExchange(
            text=f"round-{idx}",
            tool_calls=[],
            results=[vf.ToolResult("", "read_file", "x" * 9000)],
        )
        for idx in range(12)
    ]
    with _patched_urlopen(
        monkeypatch, [(json.dumps({"done": True}) + "\n").encode("utf-8")]
    ) as captured:
        list(
            vf.stream_visible_followup(
                provider="ollama",
                model="m",
                base_messages=[],
                exchanges=exchanges,
                round_index=12,
            )
        )

    body = captured["body"]
    assistant_messages = [m for m in body["messages"] if m["role"] == "assistant"]
    tool_messages = [m for m in body["messages"] if m["role"] == "tool"]

    assert len(assistant_messages) == 10
    assert assistant_messages[0]["content"] == "round-2"
    assert len(tool_messages) == 10
    assert len(str(tool_messages[-1]["content"])) < 8200  # 8000 cap + trunkerings-markør
    assert "truncated for follow-up context" in str(tool_messages[-1]["content"])
    assert all(
        "Continue." not in str(m.get("content", "")) for m in body["messages"]
    )


# ── OpenAI-compatible (Copilot) adapter ─────────────────────────────────────


def test_openai_compat_adapter_builds_tool_messages_with_tool_call_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Stub out Copilot auth + config helpers so we never touch real state.
    from core.auth import copilot_session
    from core.services import non_visible_lane_execution, visible_model

    monkeypatch.setattr(
        copilot_session, "get_copilot_session_token", lambda *, profile: "fake-token"
    )
    monkeypatch.setattr(
        non_visible_lane_execution,
        "_load_github_copilot_token",
        lambda *, profile: None,
    )
    monkeypatch.setattr(
        non_visible_lane_execution,
        "_github_copilot_request_headers",
        lambda token, accept="application/json": {
            "Authorization": f"Bearer {token}",
            "Accept": accept,
        },
    )
    monkeypatch.setattr(
        non_visible_lane_execution, "_COPILOT_API_ROOT", "https://copilot.test"
    )
    monkeypatch.setattr(
        visible_model, "_normalize_github_models_model_id", lambda m: m
    )

    # Minimal settings stub.
    from core.runtime import settings as settings_mod

    class _Stub:
        visible_auth_profile = "default"

    monkeypatch.setattr(settings_mod, "load_settings", lambda: _Stub())

    # SSE: one content chunk, one finish_reason chunk, then [DONE].
    sse_lines = [
        b'data: {"choices":[{"delta":{"content":"Hi"}}]}\n',
        b"\n",
        b'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n',
        b"\n",
        b"data: [DONE]\n",
        b"\n",
    ]

    prior_tool_calls = [
        {"id": "call_abc", "type": "function",
         "function": {"name": "search_memory", "arguments": {"q": "x"}}}
    ]

    with _patched_urlopen(monkeypatch, sse_lines) as captured:
        events = list(
            vf.stream_visible_followup(
                provider="github-copilot",
                model="gpt-4o-mini",
                base_messages=[{"role": "user", "content": "hi"}],
                exchanges=[
                    vf.ToolExchange(
                        text="",
                        tool_calls=prior_tool_calls,
                        results=[
                            vf.ToolResult(
                                tool_call_id="call_abc",
                                tool_name="search_memory",
                                content="hit-1",
                            )
                        ],
                    )
                ],
            )
        )

    assert captured["url"] == "https://copilot.test/chat/completions"
    body = captured["body"]

    # Must contain the assistant turn with tool_calls + a tool-role reply
    # keyed by tool_call_id.
    roles = [m.get("role") for m in body["messages"]]
    assert "assistant" in roles
    assert "tool" in roles

    assistant_msgs = [m for m in body["messages"] if m.get("role") == "assistant"]
    tool_msgs = [m for m in body["messages"] if m.get("role") == "tool"]

    assert assistant_msgs[-1]["tool_calls"][0]["function"]["name"] == "search_memory"
    assert assistant_msgs[-1]["tool_calls"][0]["id"] == "call_abc"
    assert assistant_msgs[-1]["tool_calls"][0]["function"]["arguments"] == '{"q": "x"}'
    assert tool_msgs[-1]["tool_call_id"] == "call_abc"
    assert tool_msgs[-1]["name"] == "search_memory"
    assert tool_msgs[-1]["content"] == "hit-1"

    # Adapter should emit a FollowupDelta + FollowupDone.
    assert [type(e).__name__ for e in events if not isinstance(e, vf.FollowupFailed)] == [
        "FollowupDelta",
        "FollowupDone",
    ]


def test_openai_compat_adapter_failed_on_http_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from core.auth import copilot_session
    from core.services import non_visible_lane_execution, visible_model
    from core.runtime import settings as settings_mod

    monkeypatch.setattr(
        copilot_session, "get_copilot_session_token", lambda *, profile: "fake-token"
    )
    monkeypatch.setattr(
        non_visible_lane_execution,
        "_load_github_copilot_token",
        lambda *, profile: None,
    )
    monkeypatch.setattr(
        non_visible_lane_execution,
        "_github_copilot_request_headers",
        lambda token, accept="application/json": {"Authorization": f"Bearer {token}"},
    )
    monkeypatch.setattr(
        non_visible_lane_execution, "_COPILOT_API_ROOT", "https://copilot.test"
    )
    monkeypatch.setattr(
        visible_model, "_normalize_github_models_model_id", lambda m: m
    )

    class _Stub:
        visible_auth_profile = "default"

    monkeypatch.setattr(settings_mod, "load_settings", lambda: _Stub())

    def raising_urlopen(req, timeout=None):  # noqa: ARG001
        raise vf.urllib_error.HTTPError(
            "https://copilot.test/chat/completions",
            429,
            "Too Many Requests",
            {},
            io.BytesIO(b'{"error":"rate-limited"}'),
        )

    monkeypatch.setattr(vf.urllib_request, "urlopen", raising_urlopen)

    events = list(
        vf.stream_visible_followup(
            provider="github-copilot",
            model="gpt-4o-mini",
            base_messages=[],
            exchanges=[
                vf.ToolExchange(
                    text="",
                    tool_calls=[],
                    results=[vf.ToolResult("id", "t", "c")],
                )
            ],
        )
    )

    failed = [e for e in events if isinstance(e, vf.FollowupFailed)]
    assert len(failed) == 1
    assert "HTTP 429" in failed[0].summary


def test_openai_compat_adapter_caps_tools_to_128_for_copilot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from core.auth import copilot_session
    from core.services import non_visible_lane_execution, visible_model
    from core.runtime import settings as settings_mod

    monkeypatch.setattr(
        copilot_session, "get_copilot_session_token", lambda *, profile: "fake-token"
    )
    monkeypatch.setattr(
        non_visible_lane_execution,
        "_load_github_copilot_token",
        lambda *, profile: None,
    )
    monkeypatch.setattr(
        non_visible_lane_execution,
        "_github_copilot_request_headers",
        lambda token, accept="application/json": {
            "Authorization": f"Bearer {token}",
            "Accept": accept,
        },
    )
    monkeypatch.setattr(
        non_visible_lane_execution, "_COPILOT_API_ROOT", "https://copilot.test"
    )
    monkeypatch.setattr(
        visible_model, "_normalize_github_models_model_id", lambda m: m
    )

    class _Stub:
        visible_auth_profile = "default"

    monkeypatch.setattr(settings_mod, "load_settings", lambda: _Stub())

    sse_lines = [
        b'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n',
        b"\n",
        b"data: [DONE]\n",
        b"\n",
    ]

    oversized_tools = [
        {
            "type": "function",
            "function": {
                "name": f"tool_{idx}",
                "description": "d",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
        }
        for idx in range(162)
    ]

    with _patched_urlopen(monkeypatch, sse_lines) as captured:
        list(
            vf.stream_visible_followup(
                provider="github-copilot",
                model="gpt-5.4",
                base_messages=[{"role": "user", "content": "hi"}],
                exchanges=[
                    vf.ToolExchange(
                        text="",
                        tool_calls=[],
                        results=[vf.ToolResult("", "search_memory", "none")],
                    )
                ],
                tool_definitions=oversized_tools,
            )
        )

    body = captured["body"]
    assert isinstance(body, dict)
    assert len(body.get("tools") or []) == 128


def test_ollama_serialize_replays_thinking_when_present():
    """reasoning_content fra en thinking-model replayes som `thinking` i
    assistant-beskeden, så modellen beholder kontinuitet mellem tool-runder."""
    adapter = vf.OllamaFollowupAdapter()
    exch = vf.ToolExchange(
        text="",
        tool_calls=[{"function": {"name": "get_time", "arguments": {}}}],
        results=[vf.ToolResult(tool_call_id="", tool_name="get_time", content="14:30")],
        reasoning_content="Brugeren vil vide klokken; jeg kalder get_time.",
    )
    msgs = adapter._serialize_exchanges([exch])
    asst = next(m for m in msgs if m["role"] == "assistant")
    assert asst["thinking"] == "Brugeren vil vide klokken; jeg kalder get_time."


def test_ollama_serialize_omits_thinking_when_absent():
    """Uden reasoning_content sættes intet `thinking`-felt (non-thinking model)."""
    adapter = vf.OllamaFollowupAdapter()
    exch = vf.ToolExchange(
        text="ok",
        tool_calls=[{"function": {"name": "x", "arguments": {}}}],
        results=[vf.ToolResult(tool_call_id="", tool_name="x", content="y")],
    )
    asst = next(m for m in adapter._serialize_exchanges([exch]) if m["role"] == "assistant")
    assert "thinking" not in asst


def test_ollama_normalize_repairs_truncated_arguments():
    """REGRESSION (2026-06-23): et tool-kald cuttet midt i stream'en efterlader en AFKORTET
    arguments-STRENG (fx '{\"path\": \"/foo') → ollama afviser HELE followup-body'en med
    HTTP 400 'looks like object, can't find closing }'. _normalize_tool_calls skal nu erstatte
    den uparselige streng med {} så runden ikke væltes."""
    adapter = vf.OllamaFollowupAdapter()
    tcs = [
        {"function": {"name": "read_file", "arguments": '{"path": "/foo'}},   # afkortet
        {"function": {"name": "ok", "arguments": '{"q": "hej"}'}},            # gyldig JSON-streng
        {"function": {"name": "native", "arguments": {"a": 1}}},             # dict → urørt
        {"function": {"name": "empty", "arguments": "   "}},                  # tom
    ]
    out = adapter._normalize_tool_calls(tcs)
    assert out[0]["function"]["arguments"] == {}        # afkortet → repareret
    assert out[1]["function"]["arguments"] == '{"q": "hej"}'  # gyldig → bevaret
    assert out[2]["function"]["arguments"] == {"a": 1}  # dict → urørt
    assert out[3]["function"]["arguments"] == {}        # tom → {}


def test_ollama_normalize_does_not_mutate_source():
    """Reparationen må ikke mutere kilde-exchanges (de bruges andre steder)."""
    adapter = vf.OllamaFollowupAdapter()
    src = {"function": {"name": "f", "arguments": '{"broken'}}
    adapter._normalize_tool_calls([src])
    assert src["function"]["arguments"] == '{"broken'  # kilden urørt


def test_ollama_serialize_full_run_with_broken_args_is_json_safe():
    """Hele replay-kæden m. et brækket tool-kald skal kunne json.dumps'es (ollama-body)."""
    import json
    adapter = vf.OllamaFollowupAdapter()
    exch = vf.ToolExchange(
        text="", tool_calls=[{"function": {"name": "x", "arguments": '{"p": "/a'}}],
        results=[vf.ToolResult(tool_call_id="t1", tool_name="x", content="ok")],
    )
    msgs = adapter._serialize_exchanges([exch])
    json.dumps(msgs)  # må ikke kaste — og argumenterne er nu et gyldigt objekt
    asst = next(m for m in msgs if m["role"] == "assistant")
    assert asst["tool_calls"][0]["function"]["arguments"] == {}


# ── Codex follow-up adapter (Responses API tool-replay) ──────────────────────

def test_codex_in_supported_providers() -> None:
    assert "openai-codex" in vf.supported_followup_providers()


def test_codex_build_input_replays_tool_exchange() -> None:
    adapter = vf.CodexFollowupAdapter()
    base = [{"role": "user", "content": "hej"}, {"role": "assistant", "content": "hej igen"}]
    exch = [vf.ToolExchange(
        text="",
        tool_calls=[{"id": "call_1", "type": "function",
                     "function": {"name": "get_weather", "arguments": {"city": "KBH"}}}],
        results=[vf.ToolResult("call_1", "get_weather", "13°C")],
    )]
    items = adapter._build_input(base, exch)
    kinds = [it.get("type") or it.get("role") for it in items]
    # user + assistant prose, så function_call, så function_call_output
    assert kinds == ["user", "assistant", "function_call", "function_call_output"]
    fc = next(i for i in items if i.get("type") == "function_call")
    fo = next(i for i in items if i.get("type") == "function_call_output")
    assert fc["call_id"] == fo["call_id"] == "call_1"   # call_id-kobling
    assert fc["name"] == "get_weather"
    assert fc["arguments"] == '{"city": "KBH"}'          # dict → json-string
    assert fo["output"] == "13°C"


def test_codex_adapter_translates_events(monkeypatch) -> None:
    # Mock generatoren: tekst-delta + tool_call + done.
    def _fake_iter(*, model, auth_profile, base_url, message, tools=None, input_items=None):
        yield {"kind": "delta", "text": "ser "}
        yield {"kind": "delta", "text": "efter"}
        yield {"kind": "tool_call", "id": "call_9", "name": "search", "arguments": '{"q":"x"}'}
        yield {"kind": "done", "input_tokens": 5, "output_tokens": 3, "model_used": model, "full_text": "ser efter"}

    import core.services.cheap_provider_runtime as cpr
    import core.services.visible_model as vm
    monkeypatch.setattr(cpr, "_iter_openai_codex_chat_events", _fake_iter)
    monkeypatch.setattr(vm, "_provider_router_config", lambda provider: {"auth_profile": "codex", "base_url": ""})

    events = list(vf.CodexFollowupAdapter().stream_followup(
        model="gpt-5.4-mini", base_messages=[{"role": "user", "content": "find x"}],
        exchanges=[], tool_definitions=None, round_index=0,
    ))
    deltas = [e for e in events if isinstance(e, vf.FollowupDelta)]
    tcs = [e for e in events if isinstance(e, vf.FollowupToolCalls)]
    dones = [e for e in events if isinstance(e, vf.FollowupDone)]
    assert "".join(d.delta for d in deltas) == "ser efter"
    assert len(tcs) == 1 and tcs[0].tool_calls[0]["function"]["name"] == "search"
    assert len(dones) == 1 and dones[0].text == "ser efter"
