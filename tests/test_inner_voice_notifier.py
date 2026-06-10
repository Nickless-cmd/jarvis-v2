"""Tests for core/services/inner_voice_notifier.py — quiet hours."""
from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from core.services.inner_voice_notifier import _in_quiet_hours, _quiet_hours


class TestQuietHours:
    def test_default_range(self):
        start, end = _quiet_hours()
        assert start == 22
        assert end == 7


class TestInQuietHours:
    def test_midday_not_quiet(self):
        dt = datetime(2026, 6, 10, 15, 0, 0, tzinfo=ZoneInfo("Europe/Copenhagen"))
        assert not _in_quiet_hours(dt)

    def test_midnight_is_quiet(self):
        dt = datetime(2026, 6, 10, 0, 0, 0, tzinfo=ZoneInfo("Europe/Copenhagen"))
        assert _in_quiet_hours(dt)

    def test_six_am_is_quiet(self):
        dt = datetime(2026, 6, 10, 6, 0, 0, tzinfo=ZoneInfo("Europe/Copenhagen"))
        assert _in_quiet_hours(dt)

    def test_eight_am_not_quiet(self):
        dt = datetime(2026, 6, 10, 8, 0, 0, tzinfo=ZoneInfo("Europe/Copenhagen"))
        assert not _in_quiet_hours(dt)

    def test_eleven_pm_is_quiet(self):
        dt = datetime(2026, 6, 10, 23, 0, 0, tzinfo=ZoneInfo("Europe/Copenhagen"))
        assert _in_quiet_hours(dt)
