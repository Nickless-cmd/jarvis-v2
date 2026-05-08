"""Tests for cross_session_arc awareness section."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.services.prompt_sections import cross_session_arc as csa


@pytest.fixture(autouse=True)
def _reset():
    csa.invalidate_cache()
    yield
    csa.invalidate_cache()


def test_noise_filter_drops_short_titles():
    assert csa._is_noise_title("")
    assert csa._is_noise_title("v2")
    assert csa._is_noise_title("ok")


def test_noise_filter_drops_known_prefixes():
    assert csa._is_noise_title("test something")
    assert csa._is_noise_title("probe-1")
    assert csa._is_noise_title("phase2-verify")
    assert csa._is_noise_title("Discord DM — 12345")


def test_noise_filter_drops_substring_markers():
    assert csa._is_noise_title("final-perf")
    assert csa._is_noise_title("prewarm-test")
    assert csa._is_noise_title("warm-cache")


def test_noise_filter_keeps_real_titles():
    assert not csa._is_noise_title("Vi byggede en soft nudge der fyrer")
    assert not csa._is_noise_title("Refleksion over identity drift")
    assert not csa._is_noise_title("Causal graph deployment")


def test_humanize_dt_relative_strings():
    now = datetime(2026, 5, 8, 12, 0, 0, tzinfo=UTC)
    just_now = (now - timedelta(seconds=10)).isoformat()
    five_min = (now - timedelta(minutes=5)).isoformat()
    two_hours = (now - timedelta(hours=2)).isoformat()
    yesterday = (now - timedelta(days=1)).isoformat()
    three_days = (now - timedelta(days=3)).isoformat()

    assert csa._humanize_dt(just_now, now) == "lige nu"
    assert csa._humanize_dt(five_min, now) == "5 min siden"
    assert csa._humanize_dt(two_hours, now) == "2t siden"
    assert csa._humanize_dt(yesterday, now) == "i går"
    assert csa._humanize_dt(three_days, now) == "3 dage siden"


def test_section_returns_string():
    """Smoke test against live DB. Section must not raise."""
    out = csa.cross_session_arc_section()
    assert isinstance(out, str)
    if out:
        assert "📜" in out
        assert "samtale-bue" in out


def test_section_silent_on_db_error(monkeypatch):
    def boom():
        raise RuntimeError("simulated")
    monkeypatch.setattr(csa, "_fetch_recent_arc", boom)
    out = csa.cross_session_arc_section()
    assert out == ""
