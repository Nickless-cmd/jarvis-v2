"""Tests for provider_health_check.health_section.

2026-05-22 (Claude): added after dropping HH:MM:SS timestamp from the
section text. The timestamp was breaking DeepSeek's prompt cache
because the line landed in the awareness block at a position where
it became the first per-build-varying content.
"""
from __future__ import annotations
import re


class TestHealthSectionNoTimestamp:
    def test_section_omits_clock_pattern(self):
        from core.services.provider_health_check import health_section
        s = health_section()
        if s is None:
            return  # nothing to check
        assert not re.search(r"\d{1,2}:\d{2}:\d{2}", s)

    def test_section_still_reports_unreachable(self):
        """The information content (unreachable list) must still be there."""
        from unittest.mock import patch
        from core.services.provider_health_check import health_section
        with patch(
            "core.services.provider_health_check.latest_health_snapshot",
            return_value={"unreachable": ["mistral", "groq"]},
        ):
            s = health_section()
        assert s is not None
        assert "mistral" in s
        assert "groq" in s
        assert "2 unreachable" in s
