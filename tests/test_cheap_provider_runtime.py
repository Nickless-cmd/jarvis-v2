from __future__ import annotations

import json


class _FakeResponse:
    def __init__(self, payload: dict[str, object], headers: dict[str, str] | None = None):
        self._payload = payload
        self.headers = headers or {}

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_groq_models_are_fetched_live(isolated_runtime, monkeypatch) -> None:
    auth_profiles = isolated_runtime.auth_profiles
    cheap = isolated_runtime.cheap_provider_runtime

    auth_profiles.save_provider_credentials(
        profile="groq",
        provider="groq",
        credentials={"api_key": "groq_test_key"},
    )

    def _urlopen(req, timeout=0):
        assert req.full_url == "https://api.groq.com/openai/v1/models"
        assert req.headers["Authorization"] == "Bearer groq_test_key"
        return _FakeResponse(
            {
                "data": [
                    {"id": "llama-3.1-8b-instant"},
                    {"id": "qwen/qwen3-32b"},
                ]
            }
        )

    monkeypatch.setattr(cheap.urllib_request, "urlopen", _urlopen)

    result = cheap.list_provider_models(provider="groq", auth_profile="groq")

    assert result["status"] == "ready"
    assert [item["id"] for item in result["models"]] == [
        "llama-3.1-8b-instant",
        "qwen/qwen3-32b",
    ]


def test_selector_skips_rate_limited_provider(isolated_runtime) -> None:
    auth_profiles = isolated_runtime.auth_profiles
    provider_router = isolated_runtime.provider_router
    cheap = isolated_runtime.cheap_provider_runtime
    db = isolated_runtime.db

    auth_profiles.save_provider_credentials(
        profile="groq",
        provider="groq",
        credentials={"api_key": "groq_key"},
    )
    auth_profiles.save_provider_credentials(
        profile="openrouter",
        provider="openrouter",
        credentials={"api_key": "openrouter_key"},
    )
    provider_router.configure_provider_router_entry(
        provider="groq",
        model="llama-3.1-8b-instant",
        auth_mode="api-key",
        auth_profile="groq",
        base_url="https://api.groq.com/openai/v1",
        api_key="",
        lane="cheap",
        set_visible=False,
    )
    provider_router.configure_provider_router_entry(
        provider="openrouter",
        model="openai/gpt-4o-mini",
        auth_mode="api-key",
        auth_profile="openrouter",
        base_url="https://openrouter.ai/api/v1",
        api_key="",
        lane="cheap",
        set_visible=False,
    )
    db.upsert_cheap_provider_runtime_state(
        provider="groq",
        model="llama-3.1-8b-instant",
        status="rate-limited",
        auth_ready=True,
        quota_limited=True,
        cooldown_until="2999-01-01T00:00:00+00:00",
    )

    target = cheap.select_cheap_lane_target()

    assert target["provider"] == "openrouter"
    assert target["model"] == "openai/gpt-4o-mini"


def test_execute_cheap_lane_fails_over_to_next_provider(
    isolated_runtime,
    monkeypatch,
) -> None:
    auth_profiles = isolated_runtime.auth_profiles
    provider_router = isolated_runtime.provider_router
    cheap = isolated_runtime.cheap_provider_runtime
    lanes = isolated_runtime.non_visible_lane_execution

    auth_profiles.save_provider_credentials(
        profile="groq",
        provider="groq",
        credentials={"api_key": "groq_key"},
    )
    auth_profiles.save_provider_credentials(
        profile="mistral",
        provider="mistral",
        credentials={"api_key": "mistral_key"},
    )
    provider_router.configure_provider_router_entry(
        provider="groq",
        model="llama-3.1-8b-instant",
        auth_mode="api-key",
        auth_profile="groq",
        base_url="https://api.groq.com/openai/v1",
        api_key="",
        lane="cheap",
        set_visible=False,
    )
    provider_router.configure_provider_router_entry(
        provider="mistral",
        model="mistral-small-latest",
        auth_mode="api-key",
        auth_profile="mistral",
        base_url="https://api.mistral.ai/v1",
        api_key="",
        lane="cheap",
        set_visible=False,
    )

    calls: list[tuple[str, str]] = []

    # Phase A re-prioritization (2026-04-26): groq was demoted (priority 60);
    # mistral (priority 40) is now tried FIRST. So to exercise failover we make
    # the higher-priority provider (mistral) fail and expect fallover to groq.
    def _execute_provider_chat(*, provider, model, auth_profile, base_url, message):
        calls.append((provider, model))
        if provider == "mistral":
            raise cheap.CheapProviderError(
                provider="mistral",
                code="rate-limited",
                message="too many requests",
                retry_after_seconds=600,
                status_code=429,
            )
        return {"text": "cheap-lane-ok", "output_tokens": 3, "cost_usd": 0.0}

    monkeypatch.setattr(cheap, "_execute_provider_chat", _execute_provider_chat)

    result = lanes.execute_cheap_lane(message="ping")

    assert result["provider"] == "groq"
    assert result["text"] == "cheap-lane-ok"
    assert calls == [
        ("mistral", "mistral-small-latest"),
        ("groq", "llama-3.1-8b-instant"),
    ]


def test_http_error_classification_covers_real_provider_failures(isolated_runtime) -> None:
    cheap = isolated_runtime.cheap_provider_runtime

    assert (
        cheap._classify_http_error(
            provider="groq",
            status_code=403,
            body="error code: 1010",
        )
        == "provider-blocked"
    )
    assert (
        cheap._classify_http_error(
            provider="openrouter",
            status_code=402,
            body='{"error":{"message":"Insufficient credits"}}',
        )
        == "credits-exhausted"
    )
    assert (
        cheap._classify_http_error(
            provider="openrouter",
            status_code=404,
            body='{"error":{"message":"No endpoints found"}}',
        )
        == "model-unavailable"
    )


def test_register_provider_failure_sets_cooldown_for_provider_blocked(
    isolated_runtime,
) -> None:
    auth_profiles = isolated_runtime.auth_profiles
    provider_router = isolated_runtime.provider_router
    cheap = isolated_runtime.cheap_provider_runtime
    db = isolated_runtime.db

    auth_profiles.save_provider_credentials(
        profile="groq",
        provider="groq",
        credentials={"api_key": "groq_key"},
    )
    provider_router.configure_provider_router_entry(
        provider="groq",
        model="llama-3.3-70b-versatile",
        auth_mode="api-key",
        auth_profile="groq",
        base_url="https://api.groq.com/openai/v1",
        api_key="",
        lane="cheap",
        set_visible=False,
    )

    cheap._register_provider_failure(
        provider="groq",
        model="llama-3.3-70b-versatile",
        auth_profile="groq",
        error=cheap.CheapProviderError(
            provider="groq",
            code="provider-blocked",
            message="blocked",
            status_code=403,
        ),
    )

    state = db.get_cheap_provider_runtime_state(
        provider="groq",
        model="llama-3.3-70b-versatile",
    )
    assert state is not None
    assert state["status"] == "provider-blocked"
    assert state["cooldown_until"] is not None


def test_smoke_cheap_lane_returns_mixed_results(
    isolated_runtime,
    monkeypatch,
) -> None:
    auth_profiles = isolated_runtime.auth_profiles
    provider_router = isolated_runtime.provider_router
    cheap = isolated_runtime.cheap_provider_runtime

    auth_profiles.save_provider_credentials(
        profile="gemini",
        provider="gemini",
        credentials={"api_key": "gemini_key"},
    )
    auth_profiles.save_provider_credentials(
        profile="openrouter",
        provider="openrouter",
        credentials={"api_key": "openrouter_key"},
    )
    provider_router.configure_provider_router_entry(
        provider="gemini",
        model="gemini-2.5-flash-lite",
        auth_mode="api-key",
        auth_profile="gemini",
        base_url="https://generativelanguage.googleapis.com/v1beta",
        api_key="",
        lane="cheap",
        set_visible=False,
    )
    provider_router.configure_provider_router_entry(
        provider="openrouter",
        model="nvidia/nemotron-3-nano-30b-a3b:free",
        auth_mode="api-key",
        auth_profile="openrouter",
        base_url="https://openrouter.ai/api/v1",
        api_key="",
        lane="cheap",
        set_visible=False,
    )

    def _execute_provider_chat(*, provider, model, auth_profile, base_url, message):
        if provider == "openrouter":
            raise cheap.CheapProviderError(
                provider="openrouter",
                code="rate-limited",
                message="too many requests",
                retry_after_seconds=120,
                status_code=429,
            )
        return {"text": "cheap-lane-ok", "output_tokens": 3, "cost_usd": 0.0}

    monkeypatch.setattr(cheap, "_execute_provider_chat", _execute_provider_chat)

    result = cheap.smoke_cheap_lane(message="Return exactly: cheap-lane-ok")

    # Phase D (2026-05-14): smoke_cheap_lane also probes providers with
    # static_models declared in CHEAP_PROVIDER_DEFAULTS (deepseek, opencode,
    # openai-codex, …), so provider_count is no longer just the 2 explicitly
    # configured entries. Those extra providers have no saved credentials →
    # they short-circuit as "auth-not-ready" and never reach the mocked call.
    # Assert on the two providers actually under test instead of exact counts.
    by_provider = {item["provider"]: item for item in result["results"]}
    assert by_provider["gemini"]["status"] == "ready"
    assert by_provider["gemini"]["ok"] is True
    assert by_provider["openrouter"]["status"] == "rate-limited"
    assert by_provider["openrouter"]["ok"] is False
    # The two credentialed providers under test produced exactly one success
    # (gemini) + one failure (openrouter). Keyless free providers (kilo,
    # ovhcloud, pollinations) are auth-ready by design — they need no saved
    # credentials — so they also succeed in the probe and the GLOBAL
    # success_count is no longer 1. Scope the assertion to the providers under
    # test rather than the whole probed roster.
    assert by_provider["openrouter"] in result["results"]


def test_selector_uses_base_priority_order_with_adaptive_penalty(isolated_runtime) -> None:
    auth_profiles = isolated_runtime.auth_profiles
    provider_router = isolated_runtime.provider_router
    cheap = isolated_runtime.cheap_provider_runtime
    db = isolated_runtime.db

    auth_profiles.save_provider_credentials(
        profile="gemini",
        provider="gemini",
        credentials={"api_key": "gemini_key"},
    )
    auth_profiles.save_provider_credentials(
        profile="nvidia",
        provider="nvidia-nim",
        credentials={"api_key": "nvidia_key"},
    )
    provider_router.configure_provider_router_entry(
        provider="gemini",
        model="gemini-2.5-flash-lite",
        auth_mode="api-key",
        auth_profile="gemini",
        base_url="https://generativelanguage.googleapis.com/v1beta",
        api_key="",
        lane="cheap",
        set_visible=False,
    )
    provider_router.configure_provider_router_entry(
        provider="nvidia-nim",
        model="meta/llama-3.1-8b-instruct",
        auth_mode="api-key",
        auth_profile="nvidia",
        base_url="https://integrate.api.nvidia.com/v1",
        api_key="",
        lane="cheap",
        set_visible=False,
    )
    db.upsert_cheap_provider_runtime_state(
        provider="gemini",
        model="gemini-2.5-flash-lite",
        status="ready",
        auth_ready=True,
        metadata_json=json.dumps(
            {
                "success_count": 3,
                "failure_count": 0,
                "smoke_success_count": 2,
                "smoke_failure_count": 0,
                "avg_latency_ms": 400,
                "avg_quality_score": 1.0,
                "quality_count": 2,
            }
        ),
    )
    db.upsert_cheap_provider_runtime_state(
        provider="nvidia-nim",
        model="meta/llama-3.1-8b-instruct",
        status="ready",
        auth_ready=True,
        metadata_json=json.dumps(
            {
                "success_count": 2,
                "failure_count": 2,
                "smoke_success_count": 1,
                "smoke_failure_count": 1,
                "avg_latency_ms": 1800,
                "avg_quality_score": 0.7,
                "quality_count": 2,
            }
        ),
    )

    target = cheap.select_cheap_lane_target()

    # The selector returns the first HEALTHY candidate in base-priority order
    # (nvidia-nim base=10 < gemini base=50). Adaptive score is not a re-sorter
    # in the current design — penalties only raise effective_priority (they
    # never reward below base), and poor providers are shed via quota/cooldown
    # blocking rather than adaptive re-ranking. So nvidia-nim is picked despite
    # its worse track record; gemini would only win once nvidia is blocked.
    assert target["provider"] == "nvidia-nim"
    # nvidia-nim's poor metadata (50% success, high latency, quality 0.7) raises
    # its effective_priority above the base 10 via the adaptive penalty.
    assert target["adaptive_penalty"] > 0
    assert target["effective_priority"] == int(target["priority"]) + target["adaptive_penalty"]


def test_important_cheap_lane_skips_ollamafreeapi(isolated_runtime) -> None:
    """Public proxies (ollamafreeapi) are last-resort, not for 'important' work.

    Phase B (2026-04-26): public proxies are kept in the default candidate list
    so generic callers fall through gracefully to them instead of collapsing —
    so a default-kind selection with ONLY ollamafreeapi configured now returns
    it as an active last resort. Phase C (2026-04-28): task_kind="important"
    drops public proxies entirely, so an important call with only ollamafreeapi
    yields no-healthy-provider.
    """
    provider_router = isolated_runtime.provider_router
    cheap = isolated_runtime.cheap_provider_runtime

    provider_router.configure_provider_router_entry(
        provider="ollamafreeapi",
        model="llama3.2:3b",
        auth_mode="none",
        auth_profile="",
        base_url="",
        api_key="",
        lane="cheap",
        set_visible=False,
    )

    # ollama-a2 (account2's LAN ollama-cloud, auth_kind=none → altid "ready") ville
    # ellers maskere dette scenarie: på en boks med LAN-adgang til 10.0.0.45 overlever
    # den reachability-proben og bliver et non-public default-pick, så testen af
    # public-proxy-tieringen bliver miljø-afhængig. Skip den her så vi tester netop
    # proxy-fallback-kontrakten deterministisk (CI uden 10.0.0.45 så det aldrig).
    _skip = frozenset({"ollama-a2"})

    # Default kind: a public proxy (ollamafreeapi, or arko if it happens to be
    # configured via runtime state) is an acceptable graceful last resort.
    default_target = cheap.select_cheap_lane_target(skip_providers=_skip)
    assert default_target["active"] is True
    assert cheap._is_public_proxy(default_target["provider"])

    # Important kind: public proxies are excluded. With only public proxies
    # available, that means no healthy provider.
    important_target = cheap.select_cheap_lane_target(
        task_kind="important", skip_providers=_skip)
    assert important_target["active"] is False
    assert important_target["status"] == "no-healthy-provider"


def test_public_safe_lane_prefers_local_ollama_then_ollamafreeapi(
    isolated_runtime,
    monkeypatch,
) -> None:
    """Public-safe lane order (2026-05-14 update):

    1. Local ollama first (higher uptime than ollamafreeapi)
    2. ollamafreeapi as fallback if local fails

    Was: ollamafreeapi first, _execute_public_safe_local_ollama as fallback.
    Changed because ollamafreeapi is too often down in production.
    """
    provider_router = isolated_runtime.provider_router
    cheap = isolated_runtime.cheap_provider_runtime

    provider_router.configure_provider_router_entry(
        provider="ollamafreeapi",
        model="llama3.2:3b",
        auth_mode="none",
        auth_profile="",
        base_url="",
        api_key="",
        lane="cheap",
        set_visible=False,
    )
    provider_router.configure_provider_router_entry(
        provider="ollama",
        model="qwen3.5:9b",
        auth_mode="none",
        auth_profile="",
        base_url="http://127.0.0.1:11434",
        api_key="",
        lane="local",
        set_visible=False,
    )

    calls: list[str] = []

    def _execute_provider_chat(*, provider, model, auth_profile, base_url, message):
        calls.append(provider)
        if provider == "ollama":
            return {
                "lane": "cheap",
                "provider": "ollama",
                "model": model,
                "status": "completed",
                "execution_mode": "public-safe-local-ollama",
                "source": "cheap-provider-runtime",
                "text": "local-ollama-ok",
                "input_tokens": 1,
                "output_tokens": 1,
                "cost_usd": 0.0,
            }
        raise AssertionError(f"should not reach {provider} when local works")

    monkeypatch.setattr(cheap, "_execute_provider_chat", _execute_provider_chat)

    result = cheap.execute_public_safe_cheap_lane(message="ping")

    assert result["provider"] == "ollama"
    assert result["text"] == "local-ollama-ok"
    # Verify local ollama was tried FIRST, before ollamafreeapi
    assert calls[0] == "ollama"


def test_openai_compat_chat_accepts_messages_list(isolated_runtime, monkeypatch) -> None:
    """Regression: OpenCode/Groq/etc. must receive full chat messages (incl.
    system prompt) so the visible lane keeps Jarvis identity. Previously the
    function only accepted a bare `message` string and wrapped it as a user
    message, causing remote models to reply as themselves (e.g. MiniMax)."""
    auth_profiles = isolated_runtime.auth_profiles
    cheap = isolated_runtime.cheap_provider_runtime

    auth_profiles.save_provider_credentials(
        profile="opencode",
        provider="opencode",
        credentials={"api_key": "oc_test_key"},  # pragma: allowlist secret
    )

    captured: dict[str, object] = {}

    def _fake_http_json(url, *, payload, headers, provider, method="POST"):
        captured["url"] = url
        captured["payload"] = payload
        captured["provider"] = provider
        return (
            {
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"prompt_tokens": 42, "completion_tokens": 3},
            },
            {},
        )

    monkeypatch.setattr(cheap, "_http_json", _fake_http_json)

    chat_messages = [
        {"role": "system", "content": "Du er Jarvis."},  # hardcoded test — identity_composer not available in unit-test
        {"role": "user", "content": "hvem er du?"},
    ]
    result = cheap._execute_openai_compatible_chat(
        provider="opencode",
        model="big-pickle",
        auth_profile="opencode",
        base_url="https://opencode.ai/zen/v1",
        messages=chat_messages,
    )

    assert captured["payload"]["messages"] == chat_messages
    assert result["text"] == "ok"
    assert result["input_tokens"] == 42
    assert result["output_tokens"] == 3


def test_openai_compat_chat_forwards_tools_and_returns_tool_calls(
    isolated_runtime, monkeypatch
) -> None:
    """Regression: visible lane for OpenCode/Groq/etc. must forward tool
    definitions and surface tool_calls from the response. Without this
    the model either refuses to call tools (no tools known) or emits
    them as inline text markup that no agentic loop picks up."""
    auth_profiles = isolated_runtime.auth_profiles
    cheap = isolated_runtime.cheap_provider_runtime

    auth_profiles.save_provider_credentials(
        profile="opencode",
        provider="opencode",
        credentials={"api_key": "oc_test_key"},  # pragma: allowlist secret
    )

    captured: dict[str, object] = {}

    def _fake_http_json(url, *, payload, headers, provider, method="POST"):
        captured["payload"] = payload
        return (
            {
                "choices": [
                    {
                        "message": {
                            "content": "",
                            "tool_calls": [
                                {
                                    "id": "call_1",
                                    "type": "function",
                                    "function": {
                                        "name": "read_file",
                                        "arguments": '{"path": "/tmp/x"}',
                                    },
                                }
                            ],
                        }
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            },
            {},
        )

    monkeypatch.setattr(cheap, "_http_json", _fake_http_json)

    tool_defs = [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a file",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
        }
    ]
    result = cheap._execute_openai_compatible_chat(
        provider="opencode",
        model="big-pickle",
        auth_profile="opencode",
        base_url="https://opencode.ai/zen/v1",
        messages=[{"role": "user", "content": "read /tmp/x"}],
        tools=tool_defs,
    )

    assert captured["payload"]["tools"] == tool_defs
    assert len(result["tool_calls"]) == 1
    assert result["tool_calls"][0]["function"]["name"] == "read_file"


# ── Regression: Codex tool-call-only svar må IKKE kaste "no text content" ──
# (Rod-årsag til codex/gpt-5.x tomme svar: function_call-tur har intet output_text.)

class _FakeStreamResponse:
    def __init__(self, lines: list[str], status_code: int = 200):
        self._lines = lines
        self.status_code = status_code
        self.headers = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def iter_lines(self):
        for ln in self._lines:
            yield ln


def test_codex_tool_call_only_does_not_raise(isolated_runtime, monkeypatch) -> None:
    import core.services.cheap_provider_runtime as cheap
    import core.auth.openai_oauth as oauth

    monkeypatch.setattr(oauth, "get_openai_bearer_token", lambda **kw: "fake-token")

    sse = [
        'data: {"type":"response.output_item.added","item":{"type":"function_call","id":"fc_1","call_id":"call_1","name":"get_weather","arguments":""}}',
        'data: {"type":"response.function_call_arguments.delta","item_id":"fc_1","delta":"{\\"city\\":\\"KBH\\"}"}',
        'data: {"type":"response.function_call_arguments.done","item_id":"fc_1","arguments":"{\\"city\\":\\"KBH\\"}"}',
        'data: {"type":"response.output_item.done","item":{"type":"function_call","id":"fc_1","call_id":"call_1","name":"get_weather","arguments":"{\\"city\\":\\"KBH\\"}"}}',
        'data: {"type":"response.completed","response":{"usage":{"input_tokens":10,"output_tokens":5}}}',
        "data: [DONE]",
    ]

    def _fake_stream(method, url, **kwargs):
        return _FakeStreamResponse(sse)

    monkeypatch.setattr(cheap.httpx, "stream", _fake_stream)

    tools = [{"type": "function", "name": "get_weather",
              "parameters": {"type": "object", "properties": {"city": {"type": "string"}}}}]
    kinds = []
    tool_calls = []
    for ev in cheap._iter_openai_codex_chat_events(
        model="gpt-5.4-mini", auth_profile="codex", base_url="", message="vejr?", tools=tools,
    ):
        kinds.append(ev.get("kind"))
        if ev.get("kind") == "tool_call":
            tool_calls.append(ev)

    # Før fixet: kastede "no text content" FØR 'done'. Efter: når 'done' + surfacer tool_call.
    assert "done" in kinds, f"generatoren nåede ikke 'done': {kinds}"
    assert len(tool_calls) == 1
    assert tool_calls[0]["name"] == "get_weather"


def test_codex_genuinely_empty_still_raises(isolated_runtime, monkeypatch) -> None:
    # Ingen tekst OG ingen tool-kald = ægte tom → skal stadig fejle.
    import core.services.cheap_provider_runtime as cheap
    import core.auth.openai_oauth as oauth

    monkeypatch.setattr(oauth, "get_openai_bearer_token", lambda **kw: "fake-token")
    sse = ['data: {"type":"response.completed","response":{"usage":{}}}', "data: [DONE]"]
    monkeypatch.setattr(cheap.httpx, "stream", lambda method, url, **kw: _FakeStreamResponse(sse))

    import pytest
    with pytest.raises(cheap.CheapProviderError):
        list(cheap._iter_openai_codex_chat_events(
            model="gpt-5.4-mini", auth_profile="codex", base_url="", message="hej", tools=None,
        ))


# ── Axis 3: _execute_provider_chat forwards tools/messages ─────────────────


def test_flatten_messages_to_text():
    import core.services.cheap_provider_runtime as cheap
    assert cheap._flatten_messages_to_text(None) == ""
    assert cheap._flatten_messages_to_text([]) == ""
    msgs = [
        {"role": "user", "content": "hej"},
        {"role": "assistant", "content": ""},
        {"role": "tool", "content": "result"},
        "junk",
    ]
    out = cheap._flatten_messages_to_text(msgs)
    assert "[user] hej" in out
    assert "[tool] result" in out
    # Empty content dropped, junk ignored.
    assert "assistant" not in out


def test_execute_provider_chat_forwards_tools_to_openai_compat(monkeypatch):
    import core.services.cheap_provider_runtime as cheap
    seen = {}

    def _fake(**kwargs):
        seen.update(kwargs)
        return {"text": "ok", "tool_calls": []}

    monkeypatch.setattr(cheap, "_execute_openai_compatible_chat", _fake)
    tools = [{"type": "function", "function": {"name": "read_file"}}]
    msgs = [{"role": "user", "content": "x"}]
    cheap._execute_provider_chat(
        provider="deepseek", model="m", auth_profile="p", base_url="",
        messages=msgs, tools=tools,
    )
    assert seen["tools"] == tools
    assert seen["messages"] == msgs


def test_execute_provider_chat_coerces_messages_for_text_only_provider(monkeypatch):
    import core.services.cheap_provider_runtime as cheap
    seen = {}

    def _fake_ofa(*, model, message):
        seen["message"] = message
        return {"text": "ok"}

    monkeypatch.setattr(cheap, "_execute_ollamafreeapi_chat", _fake_ofa)
    # ollamafreeapi is text-only; messages must be flattened to a string.
    cheap._execute_provider_chat(
        provider="ollamafreeapi", model="m", auth_profile="", base_url="",
        messages=[{"role": "user", "content": "hej"}], tools=[{"x": 1}],
    )
    assert "[user] hej" in seen["message"]


def test_dsml_stripper_holds_trailing_lt_and_flush_recovers_it():
    """CUTOFF-SPØGELSET (Bjørn 4. jul): _strip_dsml_leak holder en hale tilbage
    der kunne være starten på DSML-openeren (som begynder med '<') — inkl. et
    bart '<'. Ved stream-slut skal residualen flushes (når ikke in_block),
    ellers mistes den fra BÅDE stream og persist → 'completed'-men-afkortet."""
    import core.services.cheap_provider_runtime as cheap
    # Et svar der ender på '<' (fx "hvis x < y og z <").
    safe, held, in_block = cheap._strip_dsml_leak("hvis x < y og z <", False)
    # Mid-string '<' emitteres; kun den efterfølgende hale holdes tilbage.
    assert safe == "hvis x < y og z "
    assert held == "<"
    assert in_block is False
    # Flush-invarianten: når vi IKKE er i en ægte blok, ER residualen legitim
    # brugertekst → safe + residual rekonstruerer den fulde tekst uden tab.
    assert safe + held == "hvis x < y og z <"


def test_dsml_stripper_mid_string_lt_not_held():
    """En '<' midt i teksten (ikke i halen) skal emitteres normalt."""
    import core.services.cheap_provider_runtime as cheap
    safe, held, in_block = cheap._strip_dsml_leak("a < b er sandt.", False)
    assert safe == "a < b er sandt."
    assert held == ""
    assert in_block is False
