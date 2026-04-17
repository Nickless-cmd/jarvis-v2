"""Tests for temporal_narrative.py"""
import pytest

from core.services.temporal_narrative import (
    add_beat,
    add_beat_from_affective,
    summarize_current_self,
    ask_self_question,
    format_narrative_for_prompt,
    get_thread,
    reset_temporal_narrative,
    build_temporal_narrative_surface,
)


def setup_function():
    reset_temporal_narrative()


def test_add_beat():
    result = add_beat(mood="curious", event="user asked about code")
    assert result["mood"] == "curious"
    assert result["thread_length"] == 1


def test_add_beat_from_affective():
    result = add_beat_from_affective()
    assert "mood" in result


def test_summarize_current_self_empty():
    summary = summarize_current_self()
    assert summary == "Jeg er ny her"


def test_summarize_current_self_with_beats():
    add_beat(mood="focused", event="work on code")
    add_beat(mood="curious", event="user question")
    summary = summarize_current_self()
    assert isinstance(summary, str)
    assert len(summary) > 0


def test_ask_self_question_empty():
    question = ask_self_question()
    assert question == ""


def test_format_narrative_for_prompt_empty():
    result = format_narrative_for_prompt()
    assert result == ""


def test_get_thread():
    add_beat(mood="happy", event="test")
    thread = get_thread()
    assert len(thread) == 1


def test_reset_temporal_narrative():
    add_beat(mood="test", event="test")
    reset_temporal_narrative()
    thread = get_thread()
    assert len(thread) == 0


def test_build_temporal_narrative_surface():
    add_beat(mood="neutral", event="test event")
    surface = build_temporal_narrative_surface()
    assert "active" in surface
    assert "beat_count" in surface
    assert "summary" in surface
