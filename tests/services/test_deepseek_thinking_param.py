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
