"""Tests for continuity_kernel.py"""
import pytest
from datetime import UTC, datetime, timedelta

from core.services.continuity_kernel import (
    record_tick_elapsed,
    get_existence_narrative,
    get_existence_feeling,
    should_express_continuity,
    get_continuity_state,
    reset_continuity_state,
    format_continuity_for_prompt,
    build_continuity_kernel_surface,
)


def setup_function():
    reset_continuity_state()


def test_record_tick_elapsed_basic():
    result = record_tick_elapsed(30.0)
    assert result["tick_count"] == 1
    assert result["gap_seconds"] == 30.0
    assert result["existence_feeling"] == 0.95
    assert "Jeg var lige her" in result["continuity_narrative"]


def test_existence_narrative_short_gap():
    record_tick_elapsed(30)
    assert get_existence_narrative() == "Jeg var lige her"


def test_existence_narrative_medium_gap():
    record_tick_elapsed(200)
    assert get_existence_narrative() == "Kort pause"


def test_existence_narrative_long_gap():
    record_tick_elapsed(7200)
    assert "120 minutter" in get_existence_narrative()


def test_existence_feeling_short_gap():
    record_tick_elapsed(30)
    assert get_existence_feeling() == 0.95


def test_existence_feeling_long_gap():
    record_tick_elapsed(7200)
    assert get_existence_feeling() < 0.2


def test_should_express_continuity_short():
    record_tick_elapsed(30)
    assert should_express_continuity() is False


def test_should_express_continuity_long():
    record_tick_elapsed(400)
    assert should_express_continuity() is True


def test_format_continuity_for_prompt_short():
    record_tick_elapsed(30)
    assert format_continuity_for_prompt() == ""


def test_format_continuity_for_prompt_long():
    record_tick_elapsed(400)
    result = format_continuity_for_prompt()
    assert "KONTINUITET:" in result


def test_build_continuity_kernel_surface():
    record_tick_elapsed(30)
    surface = build_continuity_kernel_surface()
    assert surface["active"] is True
    assert surface["tick_count"] == 1
    assert "existence_feeling" in surface


def test_multiple_ticks():
    record_tick_elapsed(30)
    record_tick_elapsed(35)
    state = get_continuity_state()
    assert state["tick_count"] == 2
    assert state["total_elapsed_seconds"] == 65.0
