"""Tests for visible_followup streaming dataclasses (live reasoning trace)."""
from dataclasses import FrozenInstanceError

import pytest

from core.services.visible_followup import (
    FollowupReasoningDelta,
    FollowupDelta,
    FollowupDone,
)


def test_reasoning_delta_carries_chunk():
    d = FollowupReasoningDelta(delta="Lad mig tænke…")
    assert d.delta == "Lad mig tænke…"


def test_reasoning_delta_is_frozen():
    d = FollowupReasoningDelta(delta="x")
    with pytest.raises(FrozenInstanceError):
        d.delta = "y"  # type: ignore[misc]


def test_reasoning_delta_is_distinct_from_text_delta():
    # Reasoning og prose er forskellige typer så consumers kan routes hver for
    # sig (thinking-block vs text-block).
    assert FollowupReasoningDelta(delta="a") != FollowupDelta(delta="a")


def test_done_still_carries_reasoning_for_persistence():
    # Live-delta er kun til visning; FollowupDone bærer stadig den fulde
    # reasoning_content til persistens på tværs af runder.
    done = FollowupDone(text="svar", reasoning_content="hele tanken")
    assert done.reasoning_content == "hele tanken"


def test_followup_400_body_reaches_error(monkeypatch):
    """En HTTP 400 fra Ollama skal bære providerens ÆGTE årsag (body) ud i
    FollowupFailed.error — ikke kun det nøgne 'HTTP Error 400: Bad Request'.
    Så når Gemini afviser med 'missing a thought_signature', lander DEN tekst
    i brugerens afbryd-besked (Bjørn 2026-06-16)."""
    import io
    import urllib.error
    from core.services import visible_followup as vf

    body = b'{"error":"Function call is missing a thought_signature in functionCall parts."}'

    def _raise(*a, **k):
        raise urllib.error.HTTPError("http://x/api/chat", 400, "Bad Request", {}, io.BytesIO(body))

    # Undgå config-afhængighed: hardcode base_url + lad urlopen 400'e.
    monkeypatch.setattr(vf, "_lprr", lambda: {}, raising=False)
    monkeypatch.setattr(vf.urllib_request, "urlopen", _raise)

    adapter = vf.OllamaFollowupAdapter()
    events = list(adapter.stream_followup(
        model="gemini-3-flash-preview:cloud",
        base_messages=[{"role": "user", "content": "hej"}],
        exchanges=[],
        tool_definitions=None,
    ))
    failed = [e for e in events if isinstance(e, vf.FollowupFailed)]
    assert failed, "forventede en FollowupFailed"
    assert "thought_signature" in failed[0].error


def test_code_followup_reminds_model_to_correct_a_work_marker(monkeypatch):
    from core.services import visible_followup as module
    from core.tools.tool_scoping import tool_scope
    captured = []
    class Adapter:
        def stream_followup(self, **kwargs):
            captured.append(kwargs)
            return iter(())
    monkeypatch.setitem(module._ADAPTERS, 'test', Adapter())
    original = [{'role': 'system', 'content': 'Existing instruction'}]
    with tool_scope('code'):
        list(module.stream_visible_followup(provider='test', model='m', base_messages=[], exchanges=[], trailing_messages=original))
    tail = captured[0]['trailing_messages']
    assert len(original) == 1 and tail[0] == original[0]
    assert 'Nu skal jeg måle' in tail[-1]['content']
    assert 'correct it' in tail[-1]['content']
    with tool_scope('chat'):
        list(module.stream_visible_followup(provider='test', model='m', base_messages=[], exchanges=[], trailing_messages=original))
    assert captured[1]['trailing_messages'] == original
