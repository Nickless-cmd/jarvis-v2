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

    def _execute_provider_chat(*, provider, model, auth_profile, base_url, message):
        calls.append((provider, model))
        if provider == "groq":
            raise cheap.CheapProviderError(
                provider="groq",
                code="rate-limited",
                message="too many requests",
                retry_after_seconds=600,
                status_code=429,
            )
        return {"text": "cheap-lane-ok", "output_tokens": 3, "cost_usd": 0.0}

    monkeypatch.setattr(cheap, "_execute_provider_chat", _execute_provider_chat)

    result = lanes.execute_cheap_lane(message="ping")

    assert result["provider"] == "mistral"
    assert result["text"] == "cheap-lane-ok"
    assert calls == [
        ("groq", "llama-3.1-8b-instant"),
        ("mistral", "mistral-small-latest"),
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

    assert result["provider_count"] == 2
    assert result["success_count"] == 1
    assert result["failure_count"] == 1
    assert [item["status"] for item in result["results"]] == ["ready", "rate-limited"]


def test_selector_prefers_better_adaptive_score(isolated_runtime) -> None:
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

    assert target["provider"] == "gemini"
    assert target["effective_priority"] < 30


def test_generic_cheap_lane_skips_ollamafreeapi(isolated_runtime) -> None:
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

    target = cheap.select_cheap_lane_target()

    assert target["active"] is False
    assert target["status"] == "no-healthy-provider"


def test_public_safe_lane_prefers_ollamafreeapi_and_falls_back_local(
    isolated_runtime,
    monkeypatch,
) -> None:
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

    def _execute_provider_chat(*, provider, model, auth_profile, base_url, message):
        if provider == "ollamafreeapi":
            raise cheap.CheapProviderError(
                provider="ollamafreeapi",
                code="provider-error",
                message="down",
            )
        raise AssertionError(f"unexpected provider {provider}")

    monkeypatch.setattr(cheap, "_execute_provider_chat", _execute_provider_chat)
    monkeypatch.setattr(
        cheap,
        "_execute_public_safe_local_ollama",
        lambda *, message: {
            "lane": "local",
            "provider": "ollama",
            "model": "qwen3.5:9b",
            "status": "completed",
            "execution_mode": "public-safe-local-fallback",
            "source": "cheap-provider-runtime",
            "text": "fallback-ok",
            "input_tokens": 1,
            "output_tokens": 1,
            "cost_usd": 0.0,
        },
    )

    result = cheap.execute_public_safe_cheap_lane(message="ping")

    assert result["provider"] == "ollama"
    assert result["text"] == "fallback-ok"


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
        {"role": "system", "content": "Du er Jarvis."},
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
