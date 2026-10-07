"""Tests for visible capability prompt rules."""
from __future__ import annotations

import importlib


def _get_capability_truth_instruction(compact: bool = False) -> str:
    pc = importlib.import_module("core.services.prompt_contract")
    pc = importlib.reload(pc)
    return pc._visible_capability_truth_instruction(compact=compact) or ""


def test_no_prose_ban_in_capability_rules() -> None:
    """The 'no surrounding prose' rule must be removed."""
    text = _get_capability_truth_instruction()
    assert "no surrounding prose" not in text
    assert "exactly one capability-call line" not in text


def test_prose_allowed_with_capability_tags() -> None:
    """Prompt must allow using tools freely."""
    text = _get_capability_truth_instruction()
    assert "tools" in text.lower() or "tool calling" in text.lower()


def test_path_rule_allows_context_inference() -> None:
    """Tool instructions must not restrict paths to user message only."""
    text = _get_capability_truth_instruction()
    assert "user message already names one explicit" not in text


def test_command_rule_allows_inference() -> None:
    """Tool instructions must not restrict commands to backtick format."""
    text = _get_capability_truth_instruction()
    assert "already includes one explicit command in backticks" not in text


def test_heartbeat_living_context_line_includes_experimental_prompt_fragments(
    isolated_runtime,
    monkeypatch,
) -> None:
    pc = isolated_runtime.prompt_contract

    # Mock the new living_heartbeat_cycle service (the core replacement)
    living_cycle = importlib.import_module(
        "core.services.living_heartbeat_cycle"
    )
    monkeypatch.setattr(
        living_cycle,
        "determine_life_phase",
        lambda: {
            "phase": "dreaming",
            "mood_tendency": "contemplative",
            "suggested_actions": [
                "generate_counterfactual_dreams",
                "decay_forgotten_signals",
                "check_seed_activation",
            ],
            "depth_prompt": "Giv slip på rapporteringen.",
            "play_mode": True,
            "sleep_batch": True,
        },
    )

    # Mock relationship_texture for autonomy_from_trust
    relationship = importlib.import_module(
        "core.services.relationship_texture"
    )
    monkeypatch.setattr(
        relationship,
        "derive_appropriate_autonomy_level",
        lambda: "bounded",
    )

    line = pc._heartbeat_living_context_line()

    assert "life_phase=dreaming" in line
    assert "mood_tendency=contemplative" in line
    assert "play_mode=true" in line
    assert "sleep_batch=true" in line
    assert "autonomy_from_trust=bounded" in line



def test_batching_directive_is_present() -> None:
    """Independent calls must be asked for explicitly, not conditionally.

    Measured 5 Oct 2026: 1.59 tools per round, 55% of calls following a call to
    the same tool, chains of up to 16 consecutive single bash calls of which 78%
    were read-only. The runtime already executes every tool_call in a round, so
    the shortfall was the instruction, which read "If a task needs multiple
    reads, call multiple tools" — conditional, and it did not land.
    """
    text = _get_capability_truth_instruction()
    assert "BATCH independent calls" in text
    assert "SAME round" in text


def test_batching_directive_keeps_the_sequential_guard() -> None:
    """The counter-case must survive edits, or batching turns into wrong batching.

    Dependent calls MUST stay sequential: an argument derived from a previous
    result cannot be known before that result exists. Dropping this half of the
    rule would trade latency for incorrect tool arguments.
    """
    text = _get_capability_truth_instruction()
    assert "depend on the" in text
    assert "previous call's result" in text


def test_capability_summary_also_asks_for_batching() -> None:
    """Both surfaces carry the rule — the summary line is a separate section."""
    pc = importlib.import_module("core.services.prompt_contract")
    summary = pc._visible_capability_id_summary() or ""
    assert "Batch independent tool calls" in summary
    assert "depends on a previous result" in summary
