from __future__ import annotations

from core.services.visible_outcome_text import (
    mark_mid_word_truncation,
    origin_of_session,
    preview_text,
)


def test_preview_text_preserves_short_text_and_bounds_long_text() -> None:
    assert preview_text("to   ord") == "to ord"
    assert preview_text("abcdef", limit=5) == "abcd…"


def test_mark_mid_word_truncation_preserves_terminal_text() -> None:
    assert mark_mid_word_truncation("Tre ord her") == "Tre ord her…"
    assert mark_mid_word_truncation("Tre ord her.") == "Tre ord her."
    assert mark_mid_word_truncation("kort svar") == "kort svar"


def test_origin_of_session_extracts_only_automatic_origin() -> None:
    assert origin_of_session("auto-dream-20260902") == "dream"
    assert origin_of_session("chat-123") == ""
