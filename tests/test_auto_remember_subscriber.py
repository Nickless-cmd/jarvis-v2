"""Tests for auto_remember_subscriber — salience-triggered cross-session memory."""
from __future__ import annotations

import unittest.mock as mock

import pytest


# ── _parse_json_loose ─────────────────────────────────────────────────────


def test_parse_json_loose_clean_json() -> None:
    from core.services.auto_remember_subscriber import _parse_json_loose
    d = _parse_json_loose('{"should_remember": true, "kind": "fakta"}')
    assert d is not None
    assert d["should_remember"] is True
    assert d["kind"] == "fakta"


def test_parse_json_loose_with_markdown_fence() -> None:
    from core.services.auto_remember_subscriber import _parse_json_loose
    raw = '```json\n{"should_remember": false}\n```'
    d = _parse_json_loose(raw)
    assert d is not None
    assert d["should_remember"] is False


def test_parse_json_loose_with_preamble() -> None:
    from core.services.auto_remember_subscriber import _parse_json_loose
    raw = 'Here is my answer:\n{"should_remember": true, "kind": "indsigt"}\nDone.'
    d = _parse_json_loose(raw)
    assert d is not None
    assert d["kind"] == "indsigt"


def test_parse_json_loose_garbage_returns_none() -> None:
    from core.services.auto_remember_subscriber import _parse_json_loose
    assert _parse_json_loose("not json at all") is None
    assert _parse_json_loose("") is None
    assert _parse_json_loose("{ broken") is None


# ── evaluate_turn_for_memory ──────────────────────────────────────────────


def test_evaluate_skips_short_user_text() -> None:
    from core.services.auto_remember_subscriber import evaluate_turn_for_memory
    # User text under 10 chars → skip without LLM call
    with mock.patch(
        "core.context.compact_llm.call_compact_llm"
    ) as llm_mock:
        result = evaluate_turn_for_memory("hi", "a" * 50)
    assert result is None
    llm_mock.assert_not_called()


def test_evaluate_skips_short_assistant_text() -> None:
    from core.services.auto_remember_subscriber import evaluate_turn_for_memory
    with mock.patch(
        "core.context.compact_llm.call_compact_llm"
    ) as llm_mock:
        result = evaluate_turn_for_memory("This is a real question", "Yep")
    assert result is None
    llm_mock.assert_not_called()


def test_evaluate_returns_none_when_llm_says_dont_remember() -> None:
    from core.services.auto_remember_subscriber import evaluate_turn_for_memory
    with mock.patch(
        "core.context.compact_llm.call_compact_llm",
        return_value='{"should_remember": false}',
    ):
        result = evaluate_turn_for_memory(
            "Hvad er klokken?",
            "Klokken er 14:30. Skal jeg minde dig om noget?",
        )
    assert result is None


def test_evaluate_returns_dict_when_llm_says_remember() -> None:
    from core.services.auto_remember_subscriber import evaluate_turn_for_memory
    llm_response = (
        '{"should_remember": true, '
        '"kind": "fakta", '
        '"title": "Bjørn foretrækker dansk", '
        '"content": "Bjørn vil altid have svar på dansk, uanset input.", '
        '"visibility": "personal", '
        '"domain": "relationship", '
        '"importance": 80}'
    )
    with mock.patch(
        "core.context.compact_llm.call_compact_llm",
        return_value=llm_response,
    ):
        result = evaluate_turn_for_memory(
            "Husk altid at svare på dansk fra nu af",
            "Forstået, jeg svarer på dansk fra nu af. Det er nu en stående regel.",
        )
    assert result is not None
    assert result["kind"] == "fakta"
    assert result["visibility"] == "personal"
    assert result["domain"] == "relationship"
    assert result["importance"] == 80
    assert "dansk" in result["title"].lower()


def test_evaluate_normalizes_invalid_kind_to_none() -> None:
    from core.services.auto_remember_subscriber import evaluate_turn_for_memory
    llm_response = (
        '{"should_remember": true, "kind": "not-a-real-kind", '
        '"title": "x", "content": "y", "visibility": "personal", '
        '"domain": "d", "importance": 50}'
    )
    with mock.patch(
        "core.context.compact_llm.call_compact_llm",
        return_value=llm_response,
    ):
        result = evaluate_turn_for_memory(
            "Some user message here", "Some assistant response that is long enough"
        )
    assert result is None  # invalid kind → reject entire result


def test_evaluate_normalizes_bad_visibility_to_personal() -> None:
    from core.services.auto_remember_subscriber import evaluate_turn_for_memory
    llm_response = (
        '{"should_remember": true, "kind": "indsigt", '
        '"title": "x", "content": "y", "visibility": "secret-tier", '
        '"domain": "d", "importance": 50}'
    )
    with mock.patch(
        "core.context.compact_llm.call_compact_llm",
        return_value=llm_response,
    ):
        result = evaluate_turn_for_memory(
            "Some user message here", "Some assistant response that is long enough"
        )
    assert result is not None
    assert result["visibility"] == "personal"  # safe default


def test_evaluate_clips_importance_to_0_100() -> None:
    from core.services.auto_remember_subscriber import evaluate_turn_for_memory
    llm_response = (
        '{"should_remember": true, "kind": "fakta", '
        '"title": "x", "content": "y", "visibility": "personal", '
        '"domain": "d", "importance": 500}'
    )
    with mock.patch(
        "core.context.compact_llm.call_compact_llm",
        return_value=llm_response,
    ):
        result = evaluate_turn_for_memory(
            "Some user message here", "Some assistant response that is long enough"
        )
    assert result is not None
    assert result["importance"] == 100


def test_evaluate_handles_llm_exception_gracefully() -> None:
    from core.services.auto_remember_subscriber import evaluate_turn_for_memory
    with mock.patch(
        "core.context.compact_llm.call_compact_llm",
        side_effect=RuntimeError("provider down"),
    ):
        result = evaluate_turn_for_memory(
            "Real question here", "Real answer here that is long enough"
        )
    assert result is None  # never raises


# ── Trivial-skip gates ────────────────────────────────────────────────────


def test_trivial_user_turn_detection() -> None:
    from core.services.auto_remember_subscriber import _is_trivial_user_turn
    # Pure acks → trivial
    assert _is_trivial_user_turn("ok") is True
    assert _is_trivial_user_turn("OK!") is True
    assert _is_trivial_user_turn("tak") is True
    assert _is_trivial_user_turn("👍") is True
    assert _is_trivial_user_turn("perfekt!") is True
    assert _is_trivial_user_turn("ja gør det") is True
    # Real questions / substance → NOT trivial
    assert _is_trivial_user_turn("kan vi snakke om x?") is False
    assert _is_trivial_user_turn("husk altid at svare på dansk") is False
    assert _is_trivial_user_turn("jeg har en præference for at vi gør X") is False


def test_trivial_assistant_turn_detection() -> None:
    from core.services.auto_remember_subscriber import _is_trivial_assistant_turn
    # Short acks → trivial
    assert _is_trivial_assistant_turn("Forstået.") is True
    assert _is_trivial_assistant_turn("Klar.") is True
    assert _is_trivial_assistant_turn("Done.") is True
    # Substantive replies → NOT trivial
    assert _is_trivial_assistant_turn(
        "Forstået, jeg ændrer cadence til 30 minutter nu og opdaterer config."
    ) is False
    assert _is_trivial_assistant_turn(
        "Det er en god observation. Lad mig kigge på dataen."
    ) is False


def test_evaluate_skips_trivial_user_without_llm_call() -> None:
    """Trivielle Bjørn-beskeder → ingen LLM-kald, sparet spend."""
    from core.services.auto_remember_subscriber import evaluate_turn_for_memory
    import unittest.mock as mock

    with mock.patch(
        "core.context.compact_llm.call_compact_llm"
    ) as llm_mock:
        result = evaluate_turn_for_memory(
            "ok perfekt!",
            "Tak — jeg har lagt det ind i hjernen nu, så det er klart til næste tur.",
        )
    assert result is None
    llm_mock.assert_not_called()


def test_evaluate_skips_trivial_assistant_without_llm_call() -> None:
    """Trivielle assistant-svar → ingen LLM-kald."""
    from core.services.auto_remember_subscriber import evaluate_turn_for_memory
    import unittest.mock as mock

    with mock.patch(
        "core.context.compact_llm.call_compact_llm"
    ) as llm_mock:
        result = evaluate_turn_for_memory(
            "Jeg har en vigtig beslutning til dig: skift sprog til dansk.",
            "Forstået.",
        )
    assert result is None
    llm_mock.assert_not_called()


# ── start/stop idempotence ────────────────────────────────────────────────


def test_start_stop_idempotent() -> None:
    """Start kan kaldes flere gange uden at spawne flere threads."""
    from core.services import auto_remember_subscriber as mod

    # Ensure clean state
    mod.stop_auto_remember_subscriber()
    mod._listener_thread = None

    mod.start_auto_remember_subscriber()
    t1 = mod._listener_thread
    assert t1 is not None
    assert t1.is_alive()

    mod.start_auto_remember_subscriber()  # second call should be no-op
    t2 = mod._listener_thread
    assert t2 is t1  # same thread

    mod.stop_auto_remember_subscriber()
