"""Tests for core/util/timezone.py — central Copenhagen timezone utilities."""
from __future__ import annotations

from core.util.timezone import (
    DK_ZONE, dk_now, dk_timestamp, dk_hour, dk_date_str,
    dk_time_str, dk_weekday_da, dk_weekday_en,
    is_dk_quiet_hours, from_utc_iso, time_label_dk, dk_label,
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


class TestDkLabel:
    """Dato + klokkeslæt i dansk tid — til booknings-visninger.

    Bjoern 8/11-2026: «Tilføj klokkeslæt til sheduled». Visningerne skrev
    ``run_at[:16] + 'Z'``, altsaa rå UTC, saa en booking til kl. 09:59 dansk
    stod som 08:59Z og han maatte regne om i hovedet.
    """

    def test_vintertid_er_plus_et(self):
        # November = CET (+1). 08:59Z skal blive 09:59 dansk.
        assert dk_label("2026-11-11T08:59:05.799171+00:00") == "ons 11/11 09:59"

    def test_sommertid_er_plus_to(self):
        # Juli = CEST (+2). Samme UTC-streng giver en ANDEN dansk tid —
        # det er netop fejlen en fast offset ville lave.
        assert dk_label("2026-07-11T08:59:00+00:00") == "lør 11/07 10:59"

    def test_z_suffiks_forstaas(self):
        assert dk_label("2026-12-08T17:58:30Z") == "tir 08/12 18:58"

    def test_ugedag_er_med(self):
        # Uden ugedag siger «11/11» ikke om det er i morgen eller om tre dage.
        assert dk_label("2026-11-11T08:59:00+00:00").startswith("ons ")

    def test_skrald_giver_raa_streng_ikke_nu(self):
        # Dette er forskellen paa dk_label og from_utc_iso: sidstnaevnte falder
        # tilbage til dk_now(), saa et i stykker tidsstempel ville blive vist
        # som et tidspunkt der SER rigtigt ud. En forkert tid er vaerre end en
        # synligt ulaeselig en, naar det er en forpligtelse der skal indfries.
        assert dk_label("ikke-en-tid") == "ikke-en-tid"

    def test_tom_giver_tom(self):
        assert dk_label("") == ""

    def test_naiv_streng_behandles_som_utc(self):
        assert dk_label("2026-11-11T08:59:00") == "ons 11/11 09:59"
