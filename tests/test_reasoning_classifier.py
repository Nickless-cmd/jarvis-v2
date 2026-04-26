"""Unit tests for reasoning_classifier (R1 of reasoning-layer rollout)."""
from __future__ import annotations

from core.services.reasoning_classifier import (
    classify_reasoning_tier,
    reasoning_tier_section,
)


def test_empty_message_yields_fast_tier():
    result = classify_reasoning_tier("")
    assert result["tier"] == "fast"
    assert result["score"] == 0


def test_simple_question_yields_fast_tier():
    result = classify_reasoning_tier("hvad er klokken?")
    assert result["tier"] == "fast"


def test_short_greeting_yields_fast_tier():
    result = classify_reasoning_tier("hej")
    assert result["tier"] == "fast"


def test_destructive_command_yields_deep_tier():
    result = classify_reasoning_tier("kør rm -rf på alle gamle logfiler i prod")
    assert result["tier"] == "deep"
    assert result["score"] >= 40
    assert any("destructive" in s for s in result["signals"])


def test_drop_table_yields_deep_tier():
    result = classify_reasoning_tier("drop table users i production databasen")
    assert result["tier"] == "deep"


def test_architecture_design_yields_reasoning_tier():
    result = classify_reasoning_tier(
        "design en ny arkitektur for vores reasoning layer fra bunden — "
        "først skal vi planlægge, så implementere, og til sidst teste"
    )
    assert result["tier"] in ("reasoning", "deep")
    assert result["score"] >= 25


def test_numbered_multistep_lifts_reasoning():
    result = classify_reasoning_tier(
        "1. opret fil\n2. tilføj funktion\n3. wire den ind\n4. test"
    )
    # Should at least flag multi-step
    assert result["sub_scores"]["multistep"] > 0


def test_long_input_lifts_reasoning():
    long = "udfør refaktor af " + "noget kode " * 80
    result = classify_reasoning_tier(long)
    assert result["tier"] in ("reasoning", "deep")
    assert any("long input" in s for s in result["signals"])


def test_section_returns_none_for_fast_tier():
    assert reasoning_tier_section("hej") is None


def test_section_returns_string_for_reasoning_tier():
    section = reasoning_tier_section(
        "design ny arkitektur fra bunden med flere faser"
    )
    assert section is not None
    assert "reasoning" in section.lower() or "deep" in section.lower()


def test_subscores_present():
    result = classify_reasoning_tier("noget vagt med token")
    sub = result["sub_scores"]
    for key in ("clarification", "delegation", "risk", "novelty", "multistep"):
        assert key in sub


def test_tool_exec_wrapper():
    from core.services.reasoning_classifier import _exec_reasoning_classify
    result = _exec_reasoning_classify({"message": "drop table users i prod"})
    assert result["tier"] == "deep"


def test_task_hint_combines_with_message():
    result = classify_reasoning_tier(
        "ja",
        task_hint="kør migration på production database",
    )
    assert result["tier"] == "deep"
