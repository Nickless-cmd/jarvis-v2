"""Tests for Lag 1 — Time Pin (_time_pin_section from prompt_contract)."""

from __future__ import annotations

from datetime import UTC, datetime

from core.services.prompt_contract import _time_pin_section


def test_time_pin_contains_header():
    """Time Pin should have the ⏰ TIME PIN header block."""
    result = _time_pin_section()
    assert "TIME PIN" in result
    assert "⏰" in result


def test_time_pin_contains_utc():
    """Time Pin should contain the current UTC timestamp."""
    result = _time_pin_section()
    now = datetime.now(UTC)
    year_str = str(now.year)
    month_str = now.strftime("%m")
    assert year_str in result, f"Expected {year_str} in time pin output"
    assert "UTC" in result


def test_time_pin_contains_lokal():
    """Time Pin should contain a 'Lokal (DK)' line."""
    result = _time_pin_section()
    assert "Lokal (DK)" in result


def test_time_pin_contains_brug_text():
    """Time Pin should contain the instruction to use the pin."""
    result = _time_pin_section()
    assert "Brug PRÆCIS" in result
    assert "Gæt ikke" in result


def test_time_pin_contains_bordered_block():
    """Time Pin should be wrapped in bold ⏰ borders."""
    result = _time_pin_section()
    assert result.startswith("⏰")
    # Should have at least two border lines
    border_lines = [l for l in result.split("\n") if l.startswith("⏰")]
    assert len(border_lines) >= 2


def test_time_pin_local_hour_is_reasonable():
    """Local DK hour (CEST = UTC+2) should be between 0-23."""
    result = _time_pin_section()
    # Extract local time line: "⏰ Lokal (DK): kl HH:MM, D. Måned År ⏰"
    for line in result.split("\n"):
        if "Lokal (DK)" in line:
            # Find the hour: "kl HH:MM"
            parts = line.split("kl ")[1].split(":")[0]
            hour = int(parts)
            assert 0 <= hour <= 23, f"Hour {hour} out of range 0-23"


def test_time_pin_dato_matches_utc_date():
    """The date mentioned should be consistent with UTC date."""
    now = datetime.now(UTC)
    result = _time_pin_section()
    # UTC line contains "YYYY-MM-DD HH:MM UTC"
    utc_date = now.strftime("%Y-%m-%d")
    assert utc_date in result, f"Expected {utc_date} in time pin"
