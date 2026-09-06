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
    assert done.finish_reason == "length"


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


def test_first_pass_length_cut_is_continued_before_done(monkeypatch) -> None:
    partial = "Så Antarktis er stedet hvor vi"
    continuation = "lytter efter ting udenfor standardmodellen."
    _stub_openai_compat(monkeypatch, {
        "kind": "done",
        "full_text": partial,
        "reasoning_content": "",
        "input_tokens": 66_027,
        "output_tokens": 4_097,
        "finish_reason": "length",
    })
    monkeypatch.setattr(
        "core.services.visible_followup.synthesize_continuation",
        lambda **_kwargs: continuation,
    )

    events = list(visible_model._stream_openai_compatible_model(
        provider="deepseek", model="deepseek-v4-flash", message="fortsæt",
    ))

    deltas = [event.delta for event in events if isinstance(event, visible_model.VisibleModelDelta)]
    done = [event.result for event in events if isinstance(event, visible_model.VisibleModelStreamDone)]
    assert deltas == [" " + continuation]
    assert len(done) == 1
    assert done[0].text == partial + " " + continuation
    assert done[0].finish_reason == "stop"


def test_first_pass_failed_length_recovery_is_explicit(monkeypatch) -> None:
    partial = "Så Antarktis er stedet hvor vi"
    _stub_openai_compat(monkeypatch, {
        "kind": "done",
        "full_text": partial,
        "reasoning_content": "",
        "input_tokens": 66_027,
        "output_tokens": 4_097,
        "finish_reason": "length",
    })
    monkeypatch.setattr(
        "core.services.visible_followup.synthesize_continuation",
        lambda **_kwargs: "",
    )

    events = list(visible_model._stream_openai_compatible_model(
        provider="deepseek", model="deepseek-v4-flash", message="fortsæt",
    ))

    done = [event.result for event in events if isinstance(event, visible_model.VisibleModelStreamDone)]
    assert len(done) == 1
    assert done[0].text.startswith(partial)
    assert "afkortet" in done[0].text.lower()
    assert done[0].finish_reason == "stop"


def test_first_pass_deferred_text_is_continued_before_done(monkeypatch) -> None:
    partial = "Bid 2 kommer nu — og det er dér, det rammer mig."
    continuation = "Her er bid 2: observationen ændrer ikke fortiden."
    _stub_openai_compat(monkeypatch, {
        "kind": "done",
        "full_text": partial,
        "reasoning_content": "",
        "input_tokens": 12_000,
        "output_tokens": 80,
        "finish_reason": "stop",
    })
    monkeypatch.setattr(
        "core.services.visible_followup.synthesize_continuation",
        lambda **_kwargs: continuation,
    )
    monkeypatch.setattr(
        "core.services.hollow_promise_guard.hollow_promise_guard_enabled",
        lambda: True,
    )

    events = list(visible_model._stream_openai_compatible_model(
        provider="deepseek", model="deepseek-v4-flash", message="fortsæt",
    ))

    done = [event.result for event in events if isinstance(event, visible_model.VisibleModelStreamDone)]
    assert len(done) == 1
    assert done[0].text == partial + " " + continuation
    assert done[0].finish_reason == "stop"


# ── Live reasoning i FØRSTE pas (2026-09-01) ────────────────────────────────
#
# Målt før rettelsen: deepseek-v4-flash brugte 20,66 s på at nå det første
# synlige ord, og havde da allerede sendt 1.653 tanke-bidder. Streameren
# (cheap_provider_runtime_streaming) udsendte dem som kind="reasoning_delta",
# men første-pas-adapteren havde ingen gren for dem — så de blev kasseret og
# først læst igen ved `done`. Opfølgnings-runder streamede deres ræsonnering
# live siden juni; kun første pas manglede. Resultat: tom skærm i 20 sekunder.

def _stub_stream(monkeypatch, events: list[dict]) -> None:
    monkeypatch.setattr(adapters, "_build_visible_chat_messages_for_github", lambda **_k: [])
    monkeypatch.setattr(cheap, "provider_runtime_defaults", lambda _provider: {"base_url": "http://test"})
    monkeypatch.setattr(cheap, "deepseek_model_for_thinking_mode", lambda model, _mode: model)
    monkeypatch.setattr(cheap, "_iter_openai_compatible_chat_events", lambda **_k: iter(events))
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


def _stream(events: list[dict]) -> list:
    return list(visible_model._stream_openai_compatible_model(
        provider="deepseek", model="deepseek-v4-flash", message="hej"))


import pytest as _pytest


@_pytest.mark.parametrize("mode,expected", [
    ("fast", {"thinking": {"type": "disabled"}}),
    ("think", {"reasoning_effort": "high", "thinking": {"type": "enabled"}}),
    ("deep", {"reasoning_effort": "max", "thinking": {"type": "enabled"}}),
])
def test_first_pass_sends_deepseek_thinking_params(monkeypatch, mode, expected) -> None:
    """Composerens ⚡ Fast nåede aldrig DeepSeek i den streamede første pas:
    adapteren swappede kun modelnavn (dødt siden alias-pensioneringen 24/7).
    Målt 4/9: fast-probe fik reasoning-deltas. Nu request-params."""
    seen: dict = {}
    _stub_stream(monkeypatch, [{"kind": "done", "full_text": "ok", "reasoning_content": ""}])

    def _capture(**kw):
        seen.update(kw)
        return iter([{"kind": "done", "full_text": "ok", "reasoning_content": ""}])

    monkeypatch.setattr(cheap, "_iter_openai_compatible_chat_events", _capture)
    list(visible_model._stream_openai_compatible_model(
        provider="deepseek", model="deepseek-v4-flash", message="hej", thinking_mode=mode))
    assert seen["model"] == "deepseek-v4-flash"
    assert seen["extra_body"] == expected


def test_first_pass_non_deepseek_sends_no_thinking_params(monkeypatch) -> None:
    seen: dict = {}
    _stub_stream(monkeypatch, [])

    def _capture(**kw):
        seen.update(kw)
        return iter([{"kind": "done", "full_text": "ok", "reasoning_content": ""}])

    monkeypatch.setattr(cheap, "_iter_openai_compatible_chat_events", _capture)
    list(visible_model._stream_openai_compatible_model(
        provider="groq", model="llama", message="hej", thinking_mode="fast"))
    assert seen.get("extra_body") is None


def test_first_pass_reasoning_is_streamed_live(monkeypatch) -> None:
    _stub_stream(monkeypatch, [
        {"kind": "reasoning_delta", "text": "Lad mig se paa "},
        {"kind": "reasoning_delta", "text": "tallene foerst."},
        {"kind": "delta", "text": "Svaret er 42."},
        {"kind": "done", "full_text": "Svaret er 42.",
         "reasoning_content": "Lad mig se paa tallene foerst."},
    ])
    items = _stream([])  # events kommer fra stubben
    tanker = [i.delta for i in items
              if isinstance(i, visible_model.VisibleModelReasoningDelta)]
    assert tanker == ["Lad mig se paa ", "tallene foerst."]


def test_reasoning_is_not_mixed_into_visible_text(monkeypatch) -> None:
    """Tanken må vises — men aldrig som en del af svaret."""
    _stub_stream(monkeypatch, [
        {"kind": "reasoning_delta", "text": "hemmelig tanke"},
        {"kind": "delta", "text": "Hej Bjoern."},
        {"kind": "done", "full_text": "Hej Bjoern.", "reasoning_content": "hemmelig tanke"},
    ])
    tekst = "".join(i.delta for i in _stream([])
                    if isinstance(i, visible_model.VisibleModelDelta))
    assert tekst == "Hej Bjoern."
    assert "hemmelig" not in tekst


def test_empty_reasoning_chunks_are_dropped(monkeypatch) -> None:
    _stub_stream(monkeypatch, [
        {"kind": "reasoning_delta", "text": ""},
        {"kind": "delta", "text": "ok"},
        {"kind": "done", "full_text": "ok", "reasoning_content": ""},
    ])
    assert not [i for i in _stream([])
                if isinstance(i, visible_model.VisibleModelReasoningDelta)]
