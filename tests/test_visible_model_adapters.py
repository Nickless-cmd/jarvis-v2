import core.services.cheap_provider_runtime as cheap
import core.services.visible_model as visible_model
import core.services.visible_model_adapters as adapters
import core.tools.copilot_tool_pruning as pruning
import core.tools.simple_tools as simple_tools


def _stub_openai_compat(monkeypatch, done_event: dict) -> None:
    monkeypatch.setattr(adapters, "_build_visible_chat_messages_for_github", lambda **_k: [])
    monkeypatch.setattr(cheap, "provider_runtime_defaults", lambda _provider: {"base_url": "http://test"})
    monkeypatch.setattr(cheap, "deepseek_model_for_thinking_mode", lambda model, _mode: model)
    monkeypatch.setattr(cheap, "_iter_openai_compatible_chat_events", lambda **_k: iter([done_event]))
    monkeypatch.setattr(simple_tools, "get_tool_definitions", lambda: [])
    monkeypatch.setattr(pruning, "select_tools_for_visible", lambda *_a, **_k: [])
    monkeypatch.setattr(
        "core.runtime.provider_router.load_provider_router_registry",
        lambda: {"providers": []},
    )
    monkeypatch.setattr(
        "core.services.unconscious_modulation.compute_unconscious_modulation",
        lambda **_k: (None, None),
    )


def _done_result() -> visible_model.VisibleModelResult:
    done = None
    for event in visible_model._stream_openai_compatible_model(
        provider="deepseek", model="deepseek-v4-flash", message="hej",
    ):
        if isinstance(event, visible_model.VisibleModelStreamDone):
            done = event.result
    assert done is not None
    return done


def test_truncated_reasoning_is_not_surfaced_as_visible_text(monkeypatch) -> None:
    reasoning = "Jeg skal foerst analysere dette. " * 500
    _stub_openai_compat(monkeypatch, {
        "kind": "done",
        "full_text": "",
        "reasoning_content": reasoning,
        "input_tokens": 48_000,
        "output_tokens": 4096,
        "finish_reason": "length",
    })

    done = _done_result()
    assert done.text == ""
    assert done.reasoning_content == reasoning


def test_complete_reasoning_fallback_remains_supported(monkeypatch) -> None:
    _stub_openai_compat(monkeypatch, {
        "kind": "done",
        "full_text": "",
        "reasoning_content": "Det endelige svar er 42.",
        "input_tokens": 100,
        "output_tokens": 20,
        "finish_reason": "stop",
    })

    assert _done_result().text == "Det endelige svar er 42."
