from __future__ import annotations


def test_build_past_context_section_is_retired_compatibility_noop(monkeypatch):
    from core.services import past_context_router as pcr
    import core.services.recall as recall_mod

    monkeypatch.setattr(recall_mod, "recall", lambda *a, **k: {
        "results": [{"source": "chat", "text": "Vi besluttede recall først."}],
    })

    text = pcr.build_past_context_section("kan du huske hvad vi besluttede?")
    assert text == ""


def test_build_past_context_section_skips_plain_short_turns():
    from core.services.past_context_router import build_past_context_section

    assert build_past_context_section("hej") == ""
