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
