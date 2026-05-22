"""Tests for prompt_contract module.

Currently covers the _time_pin_section function (Layer 1 of Lying Engine).
Time-pin-specific assertions also live in test_time_pin.py — this file
exists so the test-enforcement hook (scripts/enforce_test_coverage.py)
sees tests for prompt_contract.py changes.
"""
from __future__ import annotations


class TestTimePinSection:
    """Layer 1: prominent time block in every system prompt."""

    def test_includes_utc_timestamp(self):
        from core.services.prompt_contract import _time_pin_section
        out = _time_pin_section()
        assert "UTC" in out
        # Year 2026+ must appear somewhere in the rendering
        assert "202" in out

    def test_includes_local_timezone_abbrev(self):
        """CEST in summer or CET in winter — never both, never neither."""
        from core.services.prompt_contract import _time_pin_section
        out = _time_pin_section()
        has_cest = "CEST" in out
        has_cet_alone = ("CET" in out) and not has_cest
        assert has_cest or has_cet_alone, (
            "Time pin must show a Copenhagen timezone abbreviation"
        )

    def test_contains_anchor_marker(self):
        """The ⏰ emoji + TIME PIN label must be present (visual unmissability)."""
        from core.services.prompt_contract import _time_pin_section
        out = _time_pin_section()
        assert "⏰" in out
        assert "TIME PIN" in out

    def test_contains_explicit_instruction(self):
        """Must tell the model to use this, not guess."""
        from core.services.prompt_contract import _time_pin_section
        out = _time_pin_section()
        assert "Gæt ikke" in out or "Brug PRÆCIS" in out


class TestQuickFactsSection:
    """Quick Facts is loaded from QUICK_FACTS.md — exists but no time injected."""

    def test_returns_none_or_string(self, tmp_path):
        from core.services.prompt_contract import _quick_facts_section
        # Path with no QUICK_FACTS.md → returns None
        out = _quick_facts_section(workspace_dir=tmp_path)
        assert out is None
