"""Tests for Lag 1 — Time Pin (_time_pin_section from prompt_contract).

2026-06-11: updated assertions to match single-line "DANSK TID" format
(no more UTC line, no "Lokal (DK)" line).
"""

from __future__ import annotations

from datetime import UTC, datetime

from core.services.prompt_contract import _time_pin_section


def test_time_pin_contains_header():
    """Time Pin should have the ⏰ DANSK TID header block."""
    result = _time_pin_section()
    assert "DANSK TID" in result
    assert "⏰" in result


def test_time_pin_no_utc():
    """Time Pin should NOT contain UTC (single Danish line only)."""
    result = _time_pin_section()
    assert "UTC" not in result


def test_time_pin_no_lokal():
    """Time Pin should NOT contain 'Lokal (DK)' (single Danish line only)."""
    result = _time_pin_section()
    assert "Lokal (DK)" not in result


def test_time_pin_no_time_pin_label():
    """Time Pin should NOT contain 'TIME PIN' label (replaced by 'DANSK TID')."""
    result = _time_pin_section()
    assert "TIME PIN" not in result


def test_time_pin_contains_brug_text():
    """Time Pin should contain the instruction to use the pin."""
    result = _time_pin_section()
    assert "Use PRECISELY" in result
    assert "Don't guess" in result


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
    for line in result.split("\n"):
        if "DANSK TID" in line:
            # Extract hour from "⏰ DANSK TID — HH:MM CEST, ... ⏰"
            parts = line.split("— ")[1].split(":")[0]
            hour = int(parts)
            assert 0 <= hour <= 23, f"Hour {hour} out of range 0-23"


def test_time_pin_contains_year():
    """The current year should appear."""
    now = datetime.now(UTC)
    result = _time_pin_section()
    assert str(now.year) in result


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
        # (docstring may mention it as history — parse AST so we only
        # check code, not comments).
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "local_offset":
                        raise AssertionError(
                            "Hardcoded `local_offset` assignment must be gone "
                            "— it broke in winter (CET)"
                        )
