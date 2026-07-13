import core.services.cheap_provider_runtime as cra
import core.services.visible_model as vm


def test_execute_openai_compatible_chat_merges_extra_body(monkeypatch):
    from core.services.cheap_provider_runtime_adapters import (
        _execute_openai_compatible_chat,
    )
    captured = {}

    def _fake_http_json(url, *, provider, method="POST", payload=None, headers=None):
        captured["payload"] = payload
        data = {
            "choices": [{"message": {"content": "ok"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }
        return data, {}

    monkeypatch.setattr(cra, "_require_credentials",
                        lambda *, profile, provider: {"api_key": "x"})
    monkeypatch.setattr(cra, "provider_runtime_defaults",
                        lambda provider: {"base_url": "http://example"})
    monkeypatch.setattr(cra, "_http_json", _fake_http_json)

    _execute_openai_compatible_chat(
        provider="deepseek",
        model="deepseek-v4-flash",
        auth_profile="default",
        base_url="http://example",
        message="hi",
        extra_body={"thinking": {"type": "disabled"}},
    )
    assert captured["payload"]["thinking"] == {"type": "disabled"}
    assert captured["payload"]["model"] == "deepseek-v4-flash"


def test_execute_openai_compatible_chat_default_no_extra_body(monkeypatch):
    from core.services.cheap_provider_runtime_adapters import (
        _execute_openai_compatible_chat,
    )
    captured = {}

    def _fake_http_json(url, *, provider, method="POST", payload=None, headers=None):
        captured["payload"] = payload
        data = {
            "choices": [{"message": {"content": "ok"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }
        return data, {}

    monkeypatch.setattr(cra, "_require_credentials",
                        lambda *, profile, provider: {"api_key": "x"})
    monkeypatch.setattr(cra, "provider_runtime_defaults",
                        lambda provider: {"base_url": "http://example"})
    monkeypatch.setattr(cra, "_http_json", _fake_http_json)

    _execute_openai_compatible_chat(
        provider="deepseek",
        model="deepseek-v4-flash",
        auth_profile="default",
        base_url="http://example",
        message="hi",
    )
    assert "thinking" not in captured["payload"]


def test_execute_visible_model_deepseek_fast_disables_thinking(monkeypatch):
    seen = {}

    def _fake_run(*, provider, model, message, session_id, extra_body=None):
        seen["provider"], seen["model"], seen["extra_body"] = provider, model, extra_body

        class R:
            text = "ok"
        return R(), []

    monkeypatch.setattr(vm, "_run_openai_compatible_visible", _fake_run)
    vm.execute_visible_model(
        message="m", provider="deepseek", model="deepseek-v4-flash",
        thinking_mode="fast",
    )
    assert seen["model"] == "deepseek-v4-flash"
    assert seen["extra_body"] == {"thinking": {"type": "disabled"}}


def test_execute_visible_model_default_no_extra_body(monkeypatch):
    seen = {}

    def _fake_run(*, provider, model, message, session_id, extra_body=None):
        seen["extra_body"] = extra_body

        class R:
            text = "ok"
        return R(), []

    monkeypatch.setattr(vm, "_run_openai_compatible_visible", _fake_run)
    vm.execute_visible_model(
        message="m", provider="deepseek", model="deepseek-v4-flash",
    )
    assert seen["extra_body"] is None
