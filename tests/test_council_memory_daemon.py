"""Tests for council_memory_daemon — LLM similarity + injection."""
from __future__ import annotations

from unittest.mock import patch


def _tick(entries, llm_response: str):
    """Helper: tick daemon with mocked entries and LLM response."""
    from core.services import council_memory_daemon as cmd
    cmd._last_llm_call_at = None  # reset cooldown

    with (
        patch("core.services.council_memory_daemon._load_entries", return_value=entries),
        patch("core.services.council_memory_daemon._call_similarity_llm", return_value=llm_response),
    ):
        return cmd.tick_council_memory_daemon(recent_context="current conversation context")


def test_tick_skips_when_no_entries():
    result = _tick(entries=[], llm_response="ingen")
    assert result["injected"] is False
    assert result["reason"] == "no_entries"


def test_tick_injects_when_llm_returns_index():
    entries = [
        {"topic": "Autonomy", "conclusion": "Focus on autonomy.", "timestamp": "2026-04-01T10:00:00", "initiative": None},
        {"topic": "Desire", "conclusion": "Follow desire.", "timestamp": "2026-04-02T10:00:00", "initiative": None},
    ]
    result = _tick(entries=entries, llm_response="1")
    assert result["injected"] is True
    assert len(result["injected_entries"]) == 1
    assert result["injected_entries"][0]["topic"] == "Autonomy"


def test_tick_injects_two_when_llm_returns_two():
    entries = [
        {"topic": "A", "conclusion": "C1.", "timestamp": "2026-04-01T10:00:00", "initiative": None},
        {"topic": "B", "conclusion": "C2.", "timestamp": "2026-04-02T10:00:00", "initiative": None},
    ]
    result = _tick(entries=entries, llm_response="1, 2")
    assert result["injected"] is True
    assert len(result["injected_entries"]) == 2


def test_tick_skips_when_llm_returns_ingen():
    entries = [
        {"topic": "A", "conclusion": "C1.", "timestamp": "2026-04-01T10:00:00", "initiative": None},
    ]
    result = _tick(entries=entries, llm_response="ingen")
    assert result["injected"] is False
    assert result["reason"] == "no_match"


def test_tick_cooldown_prevents_rapid_calls():
    from core.services import council_memory_daemon as cmd
    from datetime import UTC, datetime
    cmd._last_llm_call_at = datetime.now(UTC)  # simulate recent call

    entries = [{"topic": "A", "conclusion": "C.", "timestamp": "t", "initiative": None}]
    with patch("core.services.council_memory_daemon._load_entries", return_value=entries):
        result = cmd.tick_council_memory_daemon(recent_context="ctx")
    assert result["injected"] is False
    assert result["reason"] == "cooldown"
    cmd._last_llm_call_at = None  # reset
