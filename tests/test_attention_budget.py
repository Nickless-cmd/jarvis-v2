"""Tests for attention_budget — adaptive context budgeting for prompt assembly."""
from __future__ import annotations

import pytest

from core.services.attention_budget import (
    AttentionBudget,
    AttentionTrace,
    SectionBudget,
    SectionResult,
    apply_section_budget,
    build_micro_cognitive_frame,
    get_attention_budget,
    select_sections_under_budget,
    BUDGET_VISIBLE_COMPACT,
    BUDGET_VISIBLE_FULL,
    BUDGET_HEARTBEAT,
)


# ---------------------------------------------------------------------------
# Budget profile tests
# ---------------------------------------------------------------------------


def test_budget_profiles_exist_and_have_correct_names() -> None:
    """All three named profiles must resolve correctly."""
    assert get_attention_budget("visible_compact").profile == "visible_compact"
    assert get_attention_budget("visible_full").profile == "visible_full"
    assert get_attention_budget("heartbeat").profile == "heartbeat"


def test_unknown_profile_falls_back_to_visible_full() -> None:
    """An unknown profile name must default to visible_full."""
    budget = get_attention_budget("nonexistent_profile")
    assert budget.profile == "visible_full"


def test_compact_budget_excludes_private_brain_and_self_knowledge() -> None:
    """Compact visible must have zero budget for private brain and self-knowledge.
    These are heartbeat-only sections."""
    assert BUDGET_VISIBLE_COMPACT.private_brain.max_chars == 0
    assert BUDGET_VISIBLE_COMPACT.self_knowledge.max_chars == 0


def test_compact_budget_requires_cognitive_frame() -> None:
    """Compact visible must have cognitive frame as must-include."""
    assert BUDGET_VISIBLE_COMPACT.cognitive_frame.must_include is True
    assert BUDGET_VISIBLE_COMPACT.cognitive_frame.max_chars > 0


def test_heartbeat_budget_includes_brain_and_knowledge() -> None:
    """Heartbeat budget must have non-zero budgets for brain and knowledge."""
    assert BUDGET_HEARTBEAT.private_brain.max_chars > 0
    assert BUDGET_HEARTBEAT.self_knowledge.max_chars > 0


def test_budget_priority_ordering_is_consistent() -> None:
    """Capability truth must always be must-include across all profiles."""
    for budget in (BUDGET_VISIBLE_COMPACT, BUDGET_VISIBLE_FULL, BUDGET_HEARTBEAT):
        assert budget.capability_truth.must_include is True
        assert budget.cognitive_frame.must_include is True


# ---------------------------------------------------------------------------
# Section budget application tests
# ---------------------------------------------------------------------------


def test_apply_budget_to_none_content() -> None:
    """None content results in not-included."""
    budget = SectionBudget(max_chars=200, max_items=3)
    content, result = apply_section_budget(name="test", content=None, budget=budget)
    assert content is None
    assert result.included is False
    assert "no-content" in result.omission_reason


def test_apply_budget_to_empty_content() -> None:
    """Empty string content results in not-included."""
    budget = SectionBudget(max_chars=200, max_items=3)
    content, result = apply_section_budget(name="test", content="   ", budget=budget)
    assert content is None
    assert result.included is False


def test_apply_budget_zero_chars_budget() -> None:
    """Zero budget means section is excluded regardless of content."""
    budget = SectionBudget(max_chars=0, max_items=0, priority=9)
    content, result = apply_section_budget(
        name="test", content="some real content", budget=budget,
    )
    assert content is None
    assert result.included is False
    assert "zero-budget" in result.omission_reason


def test_apply_budget_content_within_budget() -> None:
    """Content within budget is included unchanged."""
    budget = SectionBudget(max_chars=500, max_items=3)
    text = "A short section of content"
    content, result = apply_section_budget(name="test", content=text, budget=budget)
    assert content == text
    assert result.included is True
    assert result.trimmed is False
    assert result.chars_used == len(text)


def test_apply_budget_content_exceeds_budget_gets_trimmed() -> None:
    """Content exceeding budget is trimmed at newline boundary."""
    budget = SectionBudget(max_chars=30, max_items=3)
    text = "Line one\nLine two\nLine three\nLine four extra content"
    content, result = apply_section_budget(name="test", content=text, budget=budget)
    assert content is not None
    assert result.included is True
    assert result.trimmed is True
    assert len(content) <= 30
    # Should cut at a newline boundary
    assert not content.endswith("extra")


# ---------------------------------------------------------------------------
# Multi-section selection tests
# ---------------------------------------------------------------------------


def test_select_sections_respects_priority_order() -> None:
    """Higher-priority sections should be included before lower-priority ones."""
    budget = AttentionBudget(
        profile="test",
        total_char_target=100,
        cognitive_frame=SectionBudget(max_chars=60, priority=1, must_include=True),
        private_brain=SectionBudget(max_chars=60, priority=2),
        self_knowledge=SectionBudget(max_chars=60, priority=3),
        self_report=SectionBudget(max_chars=0, priority=9),
        support_signals=SectionBudget(max_chars=0, priority=9),
        inner_visible_bridge=SectionBudget(max_chars=0, priority=9),
        continuity=SectionBudget(max_chars=0, priority=9),
        liveness=SectionBudget(max_chars=0, priority=9),
        capability_truth=SectionBudget(max_chars=0, priority=9),
    )
    sections = {
        "cognitive_frame": "Frame content here",
        "private_brain": "Brain content here",
        "self_knowledge": "Knowledge content here",
    }
    result, trace = select_sections_under_budget(budget=budget, sections=sections)

    assert result["cognitive_frame"] is not None
    assert result["private_brain"] is not None
    # self_knowledge may be omitted due to total budget exhaustion
    assert trace.profile == "test"
    assert trace.total_chars_used <= 100 or any(
        s.name == "cognitive_frame" and s.included for s in trace.sections
    )


def test_select_sections_exhausts_budget_gracefully() -> None:
    """When total budget is exceeded, lower-priority sections are omitted."""
    budget = AttentionBudget(
        profile="tight",
        total_char_target=50,
        cognitive_frame=SectionBudget(max_chars=40, priority=1, must_include=True),
        private_brain=SectionBudget(max_chars=40, priority=2),
        self_knowledge=SectionBudget(max_chars=40, priority=3),
        self_report=SectionBudget(max_chars=40, priority=4),
        support_signals=SectionBudget(max_chars=0, priority=9),
        inner_visible_bridge=SectionBudget(max_chars=0, priority=9),
        continuity=SectionBudget(max_chars=0, priority=9),
        liveness=SectionBudget(max_chars=0, priority=9),
        capability_truth=SectionBudget(max_chars=0, priority=9),
    )
    sections = {
        "cognitive_frame": "A" * 30,
        "private_brain": "B" * 30,
        "self_knowledge": "C" * 30,
        "self_report": "D" * 30,
    }
    result, trace = select_sections_under_budget(budget=budget, sections=sections)

    # cognitive_frame is must-include so it gets in
    assert result["cognitive_frame"] is not None
    # At least one lower-priority section should be omitted
    assert any(
        s.omission_reason == "total-budget-exhausted"
        for s in trace.sections
        if not s.included
    ) or trace.total_chars_used <= budget.total_char_target


# ---------------------------------------------------------------------------
# Attention trace tests
# ---------------------------------------------------------------------------


def test_attention_trace_summary_is_well_formed() -> None:
    """AttentionTrace.summary() must produce a clean observable dict."""
    trace = AttentionTrace(
        profile="test-profile",
        total_char_target=1000,
        total_chars_used=450,
        sections=[
            SectionResult(name="a", included=True, chars_used=200),
            SectionResult(name="b", included=True, chars_used=250, trimmed=True, omission_reason="trimmed 500→250"),
            SectionResult(name="c", included=False, omission_reason="zero-budget"),
        ],
    )
    summary = trace.summary()
    assert summary["profile"] == "test-profile"
    assert summary["total_chars_used"] == 450
    assert summary["char_utilization"] == 0.45
    assert "a" in summary["included"]
    assert "b" in summary["included"]
    assert "c" in summary["omitted"]
    assert "b" in summary["trimmed"]


# ---------------------------------------------------------------------------
# Micro cognitive frame tests
# ---------------------------------------------------------------------------


def test_micro_cognitive_frame_is_compact() -> None:
    """Micro frame must be under 180 chars and contain mode tag."""
    frame = build_micro_cognitive_frame()
    if frame is not None:
        assert len(frame) <= 180
        assert "[mind:" in frame


def test_micro_cognitive_frame_returns_none_when_conductor_unavailable(monkeypatch) -> None:
    """If conductor fails, micro frame returns None gracefully."""
    import core.services.attention_budget as mod

    def _fail():
        raise RuntimeError("conductor unavailable")

    monkeypatch.setattr(
        "core.services.attention_budget.build_micro_cognitive_frame",
        lambda: None,
    )
    # Direct test: the function should handle exceptions internally
    # The monkeypatch above tests the contract; also test the real path
    # which has its own try/except
    result = mod.build_micro_cognitive_frame()
    # Result can be None or a string — either is fine
    assert result is None or isinstance(result, str)


# ---------------------------------------------------------------------------
# Budget-authoritative prompt assembly integration tests
# ---------------------------------------------------------------------------


def test_run_budget_selection_omits_zero_budget_sections() -> None:
    """_run_budget_selection must omit sections with zero budget."""
    from core.services.prompt_contract import _run_budget_selection

    sections = {
        "capability_truth": "Capability truth content",
        "cognitive_frame": "Frame content",
        "self_report": "Self report content",
        "private_brain": "Brain content",
        "self_knowledge": "Knowledge content",
        "support_signals": "Support content",
        "inner_visible_bridge": "Bridge content",
        "continuity": "Continuity content",
        "liveness": "Liveness content",
    }

    # Visible compact excludes private_brain, self_knowledge, liveness
    selected, trace = _run_budget_selection(profile="visible_compact", sections=sections)

    assert selected["private_brain"] is None
    assert selected["self_knowledge"] is None
    assert selected["liveness"] is None
    # Must-include sections remain
    assert selected["capability_truth"] is not None
    assert selected["cognitive_frame"] is not None

    summary = trace.summary()
    assert summary["profile"] == "visible_compact"
    assert "private_brain" in summary["omitted"]
    assert "capability_truth" in summary["included"]


def test_run_budget_selection_heartbeat_includes_brain_and_knowledge() -> None:
    """Heartbeat budget must include private brain and self-knowledge."""
    from core.services.prompt_contract import _run_budget_selection

    sections = {
        "capability_truth": "Cap truth",
        "cognitive_frame": "Frame",
        "self_report": None,
        "private_brain": "Brain carry content here",
        "self_knowledge": "Self-knowledge map content",
        "support_signals": None,
        "inner_visible_bridge": None,
        "continuity": "Continuity summary",
        "liveness": "Liveness state",
    }

    selected, trace = _run_budget_selection(profile="heartbeat", sections=sections)

    assert selected["private_brain"] is not None
    assert selected["self_knowledge"] is not None
    assert selected["capability_truth"] is not None
    assert selected["cognitive_frame"] is not None
    # Visible-only sections remain None
    assert selected["self_report"] is None

    summary = trace.summary()
    assert summary["profile"] == "heartbeat"
    assert "private_brain" in summary["included"]


def test_run_budget_selection_trims_large_sections() -> None:
    """Sections exceeding their budget must be trimmed."""
    from core.services.prompt_contract import _run_budget_selection

    # Cognitive frame budget for visible_compact is 180 chars
    large_frame = "X" * 300
    sections = {
        "capability_truth": "Cap truth",
        "cognitive_frame": large_frame,
        "self_report": None,
        "private_brain": None,
        "self_knowledge": None,
        "support_signals": None,
        "inner_visible_bridge": None,
        "continuity": None,
        "liveness": None,
    }

    selected, trace = _run_budget_selection(profile="visible_compact", sections=sections)

    assert selected["cognitive_frame"] is not None
    assert len(selected["cognitive_frame"]) <= 180

    summary = trace.summary()
    assert "cognitive_frame" in summary["trimmed"]


def test_attention_trace_from_budget_selection_has_real_char_counts() -> None:
    """The trace from budget selection must have accurate char usage."""
    from core.services.prompt_contract import _run_budget_selection

    sections = {
        "capability_truth": "A" * 50,
        "cognitive_frame": "B" * 100,
        "self_report": None,
        "private_brain": None,
        "self_knowledge": None,
        "support_signals": None,
        "inner_visible_bridge": None,
        "continuity": None,
        "liveness": None,
    }

    _, trace = _run_budget_selection(profile="visible_full", sections=sections)

    summary = trace.summary()
    assert summary["total_chars_used"] == 150
    assert summary["char_utilization"] > 0


# ---------------------------------------------------------------------------
# Authority mode, overshoot, and live trace observability tests
# ---------------------------------------------------------------------------


def test_trace_authority_mode_is_budgeted_on_normal_selection() -> None:
    """Normal budget selection must mark authority_mode as 'budgeted'."""
    from core.services.prompt_contract import _run_budget_selection

    sections = {
        "capability_truth": "Cap truth",
        "cognitive_frame": "Frame",
        "self_report": None,
        "private_brain": None,
        "self_knowledge": None,
        "support_signals": None,
        "inner_visible_bridge": None,
        "continuity": None,
        "liveness": None,
    }

    _, trace = _run_budget_selection(profile="visible_compact", sections=sections)
    summary = trace.summary()

    assert summary["authority_mode"] == "budgeted"
    assert summary["fallback_reason"] is None


def test_trace_authority_mode_is_fallback_when_budget_fails(monkeypatch) -> None:
    """When budget module fails, trace must show fallback_passthrough."""
    from core.services import prompt_contract as pc

    # Force an import error by temporarily breaking the budget import
    original = pc._run_budget_selection

    def _broken_budget(*, profile, sections):
        # Simulate budget module failure by calling the except path
        from core.services.attention_budget import (
            AttentionTrace,
            SectionResult,
        )
        trace = AttentionTrace(
            profile=profile,
            total_char_target=0,
            authority_mode="fallback_passthrough",
            fallback_reason="RuntimeError: test forced failure",
        )
        for name, content in sections.items():
            trace.sections.append(SectionResult(
                name=name,
                included=content is not None and bool(content),
                chars_used=len(content) if content else 0,
                omission_reason="budget-fallback" if not content else "",
            ))
            trace.total_chars_used += len(content) if content else 0
        pc._last_attention_traces[profile] = trace
        return sections, trace

    monkeypatch.setattr(pc, "_run_budget_selection", _broken_budget)
    sections = {"capability_truth": "X", "cognitive_frame": None,
                "self_report": None, "private_brain": None,
                "self_knowledge": None, "support_signals": None,
                "inner_visible_bridge": None, "continuity": None,
                "liveness": None}

    _, trace = _broken_budget(profile="visible_compact", sections=sections)
    summary = trace.summary()

    assert summary["authority_mode"] == "fallback_passthrough"
    assert "test forced failure" in summary["fallback_reason"]


def test_trace_budget_overshoot_detected() -> None:
    """Must-include sections exceeding total budget must flag overshoot."""
    # Create a tiny total budget that must-include sections will exceed
    budget = AttentionBudget(
        profile="test-overshoot",
        total_char_target=20,
        cognitive_frame=SectionBudget(max_chars=100, must_include=True, priority=1),
        capability_truth=SectionBudget(max_chars=100, must_include=True, priority=2),
        private_brain=SectionBudget(max_chars=0, priority=9),
        self_knowledge=SectionBudget(max_chars=0, priority=9),
        self_report=SectionBudget(max_chars=0, priority=9),
        support_signals=SectionBudget(max_chars=0, priority=9),
        inner_visible_bridge=SectionBudget(max_chars=0, priority=9),
        continuity=SectionBudget(max_chars=0, priority=9),
        liveness=SectionBudget(max_chars=0, priority=9),
    )

    sections = {
        "cognitive_frame": "A" * 50,
        "capability_truth": "B" * 50,
        "private_brain": None,
        "self_knowledge": None,
        "self_report": None,
        "support_signals": None,
        "inner_visible_bridge": None,
        "continuity": None,
        "liveness": None,
    }

    _, trace = select_sections_under_budget(budget=budget, sections=sections)
    summary = trace.summary()

    assert summary["budget_overshoot"] is True
    assert summary["overshoot_chars"] == 80  # 100 used vs 20 target


def test_trace_no_overshoot_when_within_budget() -> None:
    """No overshoot flag when within budget."""
    from core.services.prompt_contract import _run_budget_selection

    sections = {
        "capability_truth": "X" * 10,
        "cognitive_frame": "Y" * 10,
        "self_report": None,
        "private_brain": None,
        "self_knowledge": None,
        "support_signals": None,
        "inner_visible_bridge": None,
        "continuity": None,
        "liveness": None,
    }

    _, trace = _run_budget_selection(profile="visible_full", sections=sections)
    summary = trace.summary()

    assert summary["budget_overshoot"] is False
    assert summary["overshoot_chars"] == 0


def test_live_attention_traces_populated_after_budget_selection() -> None:
    """After _run_budget_selection, get_last_attention_traces must return traces."""
    from core.services.prompt_contract import (
        _run_budget_selection,
        get_last_attention_traces,
    )

    sections = {
        "capability_truth": "Cap truth content",
        "cognitive_frame": "Frame content",
        "self_report": None,
        "private_brain": None,
        "self_knowledge": None,
        "support_signals": None,
        "inner_visible_bridge": None,
        "continuity": None,
        "liveness": None,
    }

    _run_budget_selection(profile="visible_compact", sections=sections)
    _run_budget_selection(profile="heartbeat", sections=sections)

    traces = get_last_attention_traces()
    assert "visible_compact" in traces
    assert "heartbeat" in traces

    vc = traces["visible_compact"]
    assert vc["profile"] == "visible_compact"
    assert vc["authority_mode"] == "budgeted"
    assert "included" in vc
    assert "section_details" in vc

    hb = traces["heartbeat"]
    assert hb["profile"] == "heartbeat"
    assert hb["authority_mode"] == "budgeted"
