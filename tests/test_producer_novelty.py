"""Tests for core/services/producer_novelty.py — observe-only nyhed pr. producer (self-safe)."""
from __future__ import annotations

import pytest

from core.services import central_timeseries
from core.services import producer_novelty as pn


@pytest.fixture(autouse=True)
def _clean():
    pn._reset_for_tests()
    central_timeseries._reset_for_tests()
    yield
    pn._reset_for_tests()
    central_timeseries._reset_for_tests()


def test_producer_threadlocal_roundtrip():
    assert pn.get_producer() == ""
    pn.set_producer("inner_voice")
    assert pn.get_producer() == "inner_voice"
    pn.clear_producer()
    assert pn.get_producer() == ""


def test_repeated_output_is_low_novelty():
    # Samme tekst igen og igen → nyhed falder mod 0 (metronome kører tør).
    for _ in range(4):
        pn.record_output("dream", "Jeg drømte om havet og de blå bølger igen.")
    snap = pn.snapshot()
    assert snap["dream"]["calls"] == 4
    assert snap["dream"]["avg_novelty"] < 0.5  # gentagelse → lav nyhed
    # Sidste sample i tidsserien er ~0 (identisk med forrige).
    last = central_timeseries.recent("novelty", "dream", limit=1)[-1]
    assert last.value is not None and last.value < 0.2


def test_distinct_output_is_high_novelty():
    pn.record_output("self_critique", "Jeg var for hård ved mig selv i går.")
    pn.record_output("self_critique", "Ravioli, kvantefysik, en rød cykel på månen.")
    snap = pn.snapshot()
    # To vidt forskellige → høj gennemsnitlig nyhed.
    assert snap["self_critique"]["avg_novelty"] > 0.5


def test_empty_output_ignored():
    pn.record_output("x", "")
    pn.record_output("x", "   ")
    assert "x" not in pn.snapshot()


def test_attribution_falls_back_when_no_producer():
    # Uden set_producer → get_producer() = "" → kalder må selv give et navn (task_kind).
    pn.clear_producer()
    pn.record_output(pn.get_producer() or "task_kind_fallback", "noget tekst")
    assert "task_kind_fallback" in pn.snapshot()


def test_self_safe_never_raises():
    try:
        pn.record_output(None, None)  # type: ignore[arg-type]
        pn.record_output("p", 12345)  # type: ignore[arg-type]
    except Exception as e:  # pragma: no cover
        pytest.fail(f"record_output kastede: {e}")
