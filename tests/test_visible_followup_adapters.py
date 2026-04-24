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
    # Legacy Ollama shape: last message is user with "[tool]:\nresult" block.
    last_msg = body["messages"][-1]
    assert last_msg["role"] == "user"
    assert "[search_memory]:" in last_msg["content"]
    assert "result" in last_msg["content"]

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
    # Last exchange's seed prose should use "Continue." since it's the
    # latest round (index 1, which equals last_index).
    assert body["messages"][-1]["content"].startswith("Tool results:")
    assert "Continue." in body["messages"][-1]["content"]


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
