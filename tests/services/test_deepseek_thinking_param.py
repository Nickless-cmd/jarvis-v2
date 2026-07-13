from core.services.cheap_provider_runtime_adapters import (
    deepseek_request_for_thinking_mode, deepseek_model_for_thinking_mode,
)

def test_fast_uses_v4flash_non_thinking_not_deprecated_alias():
    model, extra = deepseek_request_for_thinking_mode("deepseek-v4-flash", "fast")
    assert model == "deepseek-v4-flash"
    assert extra.get("thinking", {}).get("type") == "disabled"

def test_think_high():
    model, extra = deepseek_request_for_thinking_mode("deepseek-v4-flash", "think")
    assert model == "deepseek-v4-flash"
    assert extra.get("reasoning_effort") == "high"
    assert extra.get("thinking", {}).get("type") == "enabled"

def test_deep_max():
    model, extra = deepseek_request_for_thinking_mode("deepseek-v4-flash", "deep")
    assert extra.get("reasoning_effort") == "max"

def test_pro_always_thinking_no_disable():
    model, extra = deepseek_request_for_thinking_mode("deepseek-v4-pro", "fast")
    assert model == "deepseek-v4-pro"
    assert extra == {}

def test_deprecated_alias_normalized_forward():
    model, _ = deepseek_request_for_thinking_mode("deepseek-chat", "fast")
    assert model == "deepseek-v4-flash"

def test_old_wrapper_never_returns_deprecated_alias():
    assert deepseek_model_for_thinking_mode("deepseek-v4-flash", "fast") == "deepseek-v4-flash"


def test_execute_openai_compatible_chat_rewrites_deprecated_alias(monkeypatch):
    """Send-grænse: deepseek-chat -> v4-flash + thinking:disabled (bevarer non-thinking),
    så enhver upstream-sti der stadig vælger det døende alias aldrig faktisk sender det."""
    import types
    import core.services.cheap_provider_runtime_adapters as cra
    captured = {}

    def _fake_http_json(url, *, payload, headers, provider):
        captured["payload"] = payload
        return {"choices": [{"message": {"content": "ok"}}]}, {}

    fake = types.SimpleNamespace(
        _require_credentials=lambda *, profile, provider: {"api_key": "x"},
        provider_runtime_defaults=lambda p: {"base_url": "https://api.deepseek.com/v1"},
        _http_json=_fake_http_json,
        _http_json_httpx=_fake_http_json,
    )
    monkeypatch.setattr(cra, "_facade", lambda: fake)

    cra._execute_openai_compatible_chat(
        provider="deepseek", model="deepseek-chat", auth_profile="default",
        base_url="https://api.deepseek.com/v1", message="hi",
    )
    assert captured["payload"]["model"] == "deepseek-v4-flash"
    assert captured["payload"]["thinking"] == {"type": "disabled"}


def test_execute_openai_compatible_chat_reasoner_alias_thinking_enabled(monkeypatch):
    import types
    import core.services.cheap_provider_runtime_adapters as cra
    captured = {}
    fake = types.SimpleNamespace(
        _require_credentials=lambda *, profile, provider: {"api_key": "x"},
        provider_runtime_defaults=lambda p: {"base_url": "https://api.deepseek.com/v1"},
        _http_json=lambda url, *, payload, headers, provider: (captured.__setitem__("p", payload) or ({"choices": [{"message": {"content": "ok"}}]}, {})),
        _http_json_httpx=lambda *a, **k: ({"choices": [{"message": {"content": "ok"}}]}, {}),
    )
    monkeypatch.setattr(cra, "_facade", lambda: fake)
    cra._execute_openai_compatible_chat(
        provider="deepseek", model="deepseek-reasoner", auth_profile="default",
        base_url="https://api.deepseek.com/v1", message="hi",
    )
    assert captured["p"]["model"] == "deepseek-v4-flash"
    assert captured["p"]["thinking"] == {"type": "enabled"}
