from __future__ import annotations

import pytest

from core.services.visible_runs import (
    PresentationInvariantError,
    _assert_presentation_invariant,
)


def test_allows_empty_text() -> None:
    _assert_presentation_invariant("")
    _assert_presentation_invariant("   \n  ")


def test_allows_natural_language_prose() -> None:
    _assert_presentation_invariant(
        "Jeg har tjekket dine noter og fundet to relevante indgange."
    )
    _assert_presentation_invariant("Sure, let me take a look.")


def test_allows_brackets_that_are_not_leading_markers() -> None:
    # Parentheticals / mid-sentence brackets must not trigger the guard —
    # only payloads that START with an internal marker.
    _assert_presentation_invariant("Jeg fandt dette [se nedenfor]:")
    _assert_presentation_invariant("The spec mentions a [tool_name]: idiom.")


def test_rejects_completed_marker() -> None:
    with pytest.raises(PresentationInvariantError):
        _assert_presentation_invariant("[Completed: search_memory, git_log]")


def test_rejects_bare_completed_marker() -> None:
    with pytest.raises(PresentationInvariantError):
        _assert_presentation_invariant("[Completed]")


def test_rejects_completed_marker_with_leading_whitespace() -> None:
    with pytest.raises(PresentationInvariantError):
        _assert_presentation_invariant("  \n[Completed: x]")


def test_rejects_tool_result_marker() -> None:
    with pytest.raises(PresentationInvariantError):
        _assert_presentation_invariant(
            "[search_memory]:\nfound 3 results about Jarvis"
        )


def test_rejects_various_tool_markers() -> None:
    for marker in (
        "[git_log]: commit abc123",
        "[read_model_config]: model=foo",
        "[bash]: exit 0",
        "[read_chronicles]:\nEntry from 2026-04-20",
    ):
        with pytest.raises(PresentationInvariantError):
            _assert_presentation_invariant(marker)


def test_exception_message_quotes_leaked_prefix() -> None:
    with pytest.raises(PresentationInvariantError) as exc_info:
        _assert_presentation_invariant("[Completed: leak-here]")
    assert "leak-here" in str(exc_info.value) or "Completed" in str(exc_info.value)


# ── Protokol-token-lækage (målt 3/11-2026) ──────────────────────────────────
#
# Et autonomt ROUTINE WAKEUP-run startede på ollama, fik `credits-exhausted`,
# og faldt tilbage til `aihubmix/coding-minimax-m3-free` — en gratis model uden
# værktøjsstøtte. Den skrev sine værktøjskald som rå tekst i sit eget
# token-format, og det gik direkte i chatten som et svar fra Jarvis.
#
# Vagten fandtes, men `_TOOL_CALL_LEAK_PATTERN` leder efter `[navn]: {` og så
# hverken `<]minimax[>` eller `[<tool_call>{`. Strengen nedenfor er den
# FAKTISKE tekst fra besked 243714 — ikke en genskabelse.

_MINIMAX_LEAK = (
    ']<]minimax[>[<tool_call>{analysis: "We need fulfill Danish routine. Need '
    'current time via date command. No tool definitions visible, but perhaps '
    'tools dynamically available? We need attempt.", "final": "…"}]'
    '<]minimax[>[<tool_call>\n{"cmd":"date \'+%Y-%m-%d %H:%M:%S %Z (%z)\'"}]'
    '<]minimax[>[<tool_call>\n{"city":"Svendborg, DK"}]'
)


def test_rejects_minimax_protocol_token_leak() -> None:
    with pytest.raises(PresentationInvariantError):
        _assert_presentation_invariant(_MINIMAX_LEAK)


def test_rejects_bare_tool_call_tag() -> None:
    for leak in (
        "<tool_call>{\"cmd\": \"ls\"}</tool_call>",
        "[<tool_call>{\"cmd\": \"ls\"}]",
        "Her er mit kald: <|tool_call|>",
    ):
        with pytest.raises(PresentationInvariantError):
            _assert_presentation_invariant(leak)


def test_rejects_other_models_special_tokens() -> None:
    for leak in (
        "<|im_start|>user\nhej<|im_end|>",
        "<|endoftext|>",
        "<]othermodel[>",
    ):
        with pytest.raises(PresentationInvariantError):
            _assert_presentation_invariant(leak)


def test_protocol_tokens_inside_fenced_block_are_explanation_not_leak() -> None:
    # En forklaring der VISER et token i en kodeblok er ikke en lækage. Uden
    # denne undtagelse ville vagten spise præcis de svar der beskriver fejlen.
    _assert_presentation_invariant(
        "Formatet så sådan ud:\n"
        "```\n<|im_start|>user\nhej<|im_end|>\n```\n"
        "og det er hvad modellen gjorde galt."
    )


def test_normal_prose_with_angle_brackets_still_passes() -> None:
    _assert_presentation_invariant("Jeg brugte `<div>` og sammenlignede a < b.")

