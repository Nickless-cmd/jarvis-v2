"""Tests for protected_inner_voice — focus on _voice_line LLM rollout.

2026-05-25 (Claude): _voice_line is THE protected inner voice synthesis.
Rolled out from template-only to LLM-primary with template fallback,
same pattern as _helpful_signal and _private_summary.
"""
import pytest

from core.memory.protected_inner_voice import _voice_line


@pytest.fixture(autouse=True)
def _stub_llm(monkeypatch):
    """For most tests: stub LLM to return its fallback (template).
    Tests that specifically check LLM-success path override this."""
    import core.services.inner_voice_shadow as shadow_mod
    monkeypatch.setattr(
        shadow_mod, "generate_voice_line_via_llm",
        lambda *, mood_tone, self_position, current_concern, current_pull,
        fallback, timeout_seconds=5.0: fallback,
    )


def test_template_fallback_guarded():
    out = _voice_line(
        mood_tone="guarded", self_position="careful",
        current_concern="watching errors", current_pull="settle",
    )
    assert "vagt" in out
    assert len(out) <= 200


def test_template_fallback_attentive():
    out = _voice_line(
        mood_tone="attentive", self_position="open",
        current_concern="", current_pull="",
    )
    assert "følger tæt" in out


def test_template_fallback_unknown_tone():
    out = _voice_line(
        mood_tone="weird-tone", self_position="x",
        current_concern="y", current_pull="z",
    )
    assert "prøver at holde mig samlet" in out


def test_llm_success_returned_when_available(monkeypatch):
    """When LLM succeeds, its output IS what _voice_line returns."""
    import core.services.inner_voice_shadow as shadow_mod
    monkeypatch.setattr(
        shadow_mod, "generate_voice_line_via_llm",
        lambda *, mood_tone, self_position, current_concern, current_pull,
        fallback, timeout_seconds=5.0:
            "LLM-synthesised voice: rolig og fokuseret.",
    )
    out = _voice_line(
        mood_tone="steady", self_position="x",
        current_concern="y", current_pull="z",
    )
    assert out == "LLM-synthesised voice: rolig og fokuseret."


def test_llm_exception_falls_back_to_template(monkeypatch):
    """If LLM call raises, _voice_line returns template."""
    import core.services.inner_voice_shadow as shadow_mod

    def _raises(**_kw):
        raise RuntimeError("import or LLM failure")

    monkeypatch.setattr(shadow_mod, "generate_voice_line_via_llm", _raises)

    out = _voice_line(
        mood_tone="steady", self_position="x",
        current_concern="y", current_pull="z",
    )
    assert "roligt" in out  # template's "Jeg står nogenlunde roligt"
    assert len(out) <= 200



# --- Bölge 2: egress-fri Central-puls ---
def test_records_private_egress_free():
    import inspect
    import core.memory.protected_inner_voice as mod
    src = inspect.getsource(mod)
    assert "record_private" in src
    assert "central().observe" not in src
    assert "event_bus" not in src
    assert "_emit(" not in src
