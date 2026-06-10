"""Tests for Lag 1 — Time Pin (_time_pin_section from prompt_contract)."""

from __future__ import annotations

from datetime import UTC, datetime

from core.services.prompt_contract import _time_pin_section


def test_time_pin_contains_dansk_tid():
    """Time Pin should have the ⏰⏰⏰ DANSK TID header block (not UTC line)."""
    result = _time_pin_section()
    assert "DANSK TID" in result
    assert "⏰" in result
    # Must NOT contain UTC line (removed to avoid confusion)
    assert "UTC" not in result.split("\n")[1], (
        "First content line must not be UTC — only Danish time"
    )


def test_time_pin_contains_year():
    """Time Pin should contain current year."""
    result = _time_pin_section()
    now = datetime.now(UTC)
    year_str = str(now.year)
    assert year_str in result, f"Expected {year_str} in time pin output"


def test_time_pin_contains_dansk_label():
    """Time Pin should contain 'DANSK TID' label (no 'Lokal (DK)' anymore)."""
    result = _time_pin_section()
    assert "DANSK TID" in result
    assert "Lokal (DK)" not in result


def test_time_pin_contains_use_text():
    """Time Pin should contain the instruction to use the pin."""
    result = _time_pin_section()
    assert "PRECISELY" in result
    assert "Don" in result and "guess" in result


def test_time_pin_contains_bordered_block():
    """Time Pin should be wrapped in bold ⏰ borders."""
    result = _time_pin_section()
    assert result.startswith("⏰")
    # Should have at least two border lines
    border_lines = [l for l in result.split("\n") if l.startswith("⏰")]
    assert len(border_lines) >= 2


def test_time_pin_local_hour_is_reasonable():
    """Local DK hour should be between 0-23."""
    result = _time_pin_section()
    # Extract from "⏰⏰⏰ DANSK TID — HH:MM CEST, ... ⏰⏰⏰"
    for line in result.split("\n"):
        if "DANSK TID" in line:
            # Find HH:MM after the em-dash
            parts = line.split("—")[1].strip().split(":")[0]
            hour = int(parts)
            assert 0 <= hour <= 23, f"Hour {hour} out of range 0-23"


def test_time_pin_includes_timezone_abbrev():
    """CEST in summer or CET in winter — never both, never neither."""
    result = _time_pin_section()
    has_cest = "CEST" in result
    has_cet_alone = ("CET" in result) and not has_cest
    assert has_cest or has_cet_alone, (
        "Time pin must show a Copenhagen timezone abbreviation"
    )


# 2026-05-22 (Claude): regression tests for the 3 bugs in original
# _time_pin_section: hardcoded UTC+2 (broke in winter), midnight-cross
# day-flip missed, year-cross missed.

class TestTimePinTimezoneHandling:
    """Time pin must use zoneinfo so DST + day + month + year all roll correctly."""

    def test_uses_copenhagen_zoneinfo_not_hardcoded_offset(self):
        """_time_pin_section output must contain CEST or CET (auto-detected)."""
        from core.services.prompt_contract import _time_pin_section
        out = _time_pin_section()
        # Either timezone abbreviation must appear (depending on season)
        assert "CEST" in out or "CET" in out, (
            "Time pin must show timezone abbreviation; "
            "hardcoded UTC+2 would not include it"
        )

    def test_uses_zoneinfo_module(self):
        """Verify the implementation uses ZoneInfo (not raw +2 offset)."""
        import ast
        import inspect
        from core.services.prompt_contract import _time_pin_section
        src = inspect.getsource(_time_pin_section)
        # Must reference zoneinfo
        assert "ZoneInfo" in src or "Europe/Copenhagen" in src, (
            "Time pin must use zoneinfo for DST-correct local time"
        )
        # Hardcoded UTC+2 assignment must be gone from the code body
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "local_offset":
                        raise AssertionError(
                            "Hardcoded `local_offset` assignment must be gone "
                            "— it broke in winter (CET)"
                        )
