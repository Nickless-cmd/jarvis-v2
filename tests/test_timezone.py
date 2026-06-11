"""Tests for core/util/timezone.py — central Copenhagen timezone utilities."""
from __future__ import annotations

from core.util.timezone import (
    DK_ZONE, dk_now, dk_timestamp, dk_hour, dk_date_str,
    dk_time_str, dk_weekday_da, dk_weekday_en,
    is_dk_quiet_hours, from_utc_iso, time_label_dk,
)


class TestDkNow:
    def test_returns_denmark_timezone(self):
        now = dk_now()
        assert now.tzinfo is not None
        assert str(now.tzinfo) == "Europe/Copenhagen"

    def test_dk_hour_range(self):
        h = dk_hour()
        assert 0 <= h <= 23


class TestDkTimestamp:
    def test_includes_cest_or_cet(self):
        ts = dk_timestamp()
        assert "CEST" in ts or "CET" in ts

    def test_includes_time(self):
        ts = dk_timestamp()
        assert ":" in ts


class TestDkDateStr:
    def test_dk_date_format(self):
        d = dk_date_str()
        assert "." in d
        assert len(d) > 5

    def test_contains_month_name(self):
        d = dk_date_str().lower()
        en_abbr = ["jan", "feb", "mar", "apr", "may", "jun",
                    "jul", "aug", "sep", "oct", "nov", "dec"]
        da_names = ["januar", "februar", "marts", "april", "maj", "juni",
                     "juli", "august", "september", "oktober", "november", "december"]
        assert any(m in d for m in en_abbr + da_names)


class TestDkTimeStr:
    def test_returns_24h_format(self):
        t = dk_time_str()
        parts = t.split(":")
        assert len(parts) == 2
        h, m = parts
        assert 0 <= int(h) <= 23
        assert 0 <= int(m) <= 59


class TestWeekday:
    def test_dk_weekday_is_danish(self):
        dag = dk_weekday_da()
        dage = ["mandag", "tirsdag", "onsdag", "torsdag",
                "fredag", "lørdag", "søndag"]
        assert dag in dage

    def test_en_weekday_is_english(self):
        dag = dk_weekday_en()
        dage = ["Monday", "Tuesday", "Wednesday", "Thursday",
                "Friday", "Saturday", "Sunday"]
        assert dag in dage


class TestIsDkQuietHours:
    def test_start_equals_end_returns_false(self):
        assert not is_dk_quiet_hours(22, 22)

    def test_zero_to_zero_returns_false(self):
        assert not is_dk_quiet_hours(0, 0)


class TestFromUtcIso:
    def test_converts_to_dk_timezone(self):
        dt = from_utc_iso("2026-06-10T12:00:00Z")
        assert str(dt.tzinfo) == "Europe/Copenhagen"
        assert dt.hour == 14  # June = CEST (+2)

    def test_handles_plus_offset(self):
        dt = from_utc_iso("2026-06-10T12:00:00+00:00")
        assert str(dt.tzinfo) == "Europe/Copenhagen"
        assert dt.hour == 14

    def test_empty_returns_now(self):
        dt = from_utc_iso("")
        assert str(dt.tzinfo) == "Europe/Copenhagen"

    def test_invalid_returns_now(self):
        dt = from_utc_iso("ikke-en-tid")
        assert str(dt.tzinfo) == "Europe/Copenhagen"


class TestTimeLabelDk:
    def test_converts_to_danish_time(self):
        label = time_label_dk("2026-06-10T12:00:00Z")
        assert label == "14:00"

    def test_invalid_fallback(self):
        label = time_label_dk("garbage")
        # Fallback til nuværende tid — returnerer et label i stedet for at crashe
        assert ":" in label
        assert len(label) == 5  # "HH:MM"

    def test_empty_fallback(self):
        label = time_label_dk("")
        assert label is not None
