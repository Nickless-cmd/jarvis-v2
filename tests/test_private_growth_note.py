"""Tests for private_growth_note — focus on template output invariants.

2026-05-24 (Claude): _helpful_signal got a shadow-mode pilot for the
llm_driven_inner_pipeline refactor. This file pins the production
contract: the function must return template strings unchanged
regardless of shadow-recording outcome. Shadow-side tests live in
tests/test_inner_voice_shadow.py.
"""
import pytest

from core.memory.private_growth_note import (
    _helpful_signal,
    _learning_kind,
    _lesson,
    _mistake_signal,
    build_private_growth_note_payload,
)


@pytest.fixture(autouse=True)
def _stub_shadow(monkeypatch):
    """Pin the template fallback path for these template-invariant tests.

    2026-05-25 (Claude): _helpful_signal now calls generate_helpful_signal_via_llm
    which returns the LLM output (or template fallback on failure). For tests
    that verify TEMPLATE behavior specifically, we stub the LLM generator to
    always return its fallback argument. The actual LLM path is tested in
    tests/test_inner_voice_shadow.py.
    """
    import core.services.inner_voice_shadow as shadow_mod

    # Old shadow API (kept for safety if any test path still uses it)
    monkeypatch.setattr(
        shadow_mod, "shadow_helpful_signal", lambda **kw: None,
    )
    # New sync-LLM API: always return fallback (template)
    monkeypatch.setattr(
        shadow_mod, "generate_helpful_signal_via_llm",
        lambda *, status, focus, work_signal, fallback, timeout_seconds=5.0: fallback,
    )


def test_helpful_signal_completed_returns_template_string():
    out = _helpful_signal(status="completed", focus="cache-fix", work_signal="")
    assert "holde fast" in out
    assert "cache fix" in out
    assert len(out) <= 140


def test_helpful_signal_failed_returns_careful_phrasing():
    out = _helpful_signal(status="failed", focus="restart-loop", work_signal="")
    assert "varsom" in out
    assert "restart loop" in out
    assert len(out) <= 140


def test_helpful_signal_cancelled_treated_like_failed():
    out = _helpful_signal(status="cancelled", focus="test", work_signal="")
    assert "varsom" in out


def test_helpful_signal_observe_returns_watching_phrasing():
    out = _helpful_signal(status="observe", focus="test", work_signal="")
    assert "følge tråden" in out


def test_helpful_signal_unknown_status_falls_through():
    out = _helpful_signal(status="weird-state", focus="x", work_signal="")
    assert out == "weird-state"


def test_helpful_signal_with_work_signal_appends_hint():
    out = _helpful_signal(
        status="completed",
        focus="cache",
        work_signal="completed:cache-fix",
    )
    assert "Det peger stadig" in out


def test_learning_kind_maps_status():
    assert _learning_kind(status="completed") == "reinforce"
    assert _learning_kind(status="failed") == "adjust"
    assert _learning_kind(status="cancelled") == "adjust"
    assert _learning_kind(status="observe") == "observe"
    assert _learning_kind(status="something-else") == "observe"


def test_mistake_signal_only_for_failed_or_cancelled():
    assert _mistake_signal(status="completed") == ""
    assert _mistake_signal(status="failed") == "failed"
    assert _mistake_signal(status="cancelled") == "cancelled"


def test_lesson_includes_focus():
    out = _lesson(learning_kind="reinforce", focus="cache-fix", work_signal="")
    assert "cache fix" in out
    out2 = _lesson(learning_kind="adjust", focus="restart-loop", work_signal="")
    assert "stay careful" in out2


def test_build_payload_produces_expected_shape():
    payload = build_private_growth_note_payload(
        run_id="run-1",
        work_id="work-1",
        status="completed",
        work_preview="some preview text " * 5,
        private_inner_note={
            "focus": "cache-fix",
            "work_signal": "completed:cache",
            "identity_alignment": "subordinate-to-visible",
        },
        created_at="2026-05-24T15:00:00+00:00",
    )
    assert payload["record_id"] == "private-growth-note:run-1"
    assert payload["learning_kind"] == "reinforce"
    assert "holde fast" in payload["helpful_signal"]
    assert payload["confidence"] in ("low", "medium", "high")
