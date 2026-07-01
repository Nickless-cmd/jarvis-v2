"""Tests for core/services/central_timeseries.py — per-nerve tidsserie (M0, §24.6)."""
from __future__ import annotations

import pytest

from core.services import central_timeseries as ts


@pytest.fixture(autouse=True)
def _clean():
    ts._reset_for_tests()
    yield
    ts._reset_for_tests()


def test_record_and_recent():
    ts.record("loop", "lifecycle", 1.0, meta={"kind": "runtime.x"})
    ts.record("loop", "lifecycle", 2.0)
    got = ts.recent("loop", "lifecycle")
    assert [s.value for s in got] == [1.0, 2.0]
    assert got[0].meta.get("kind") == "runtime.x"
    assert got[-1].ts  # timestamp populated


def test_per_nerve_isolation_no_cross_eviction():
    # KERNEN i §24.6: ét støjende nerve må IKKE evict'e et andet nerves historik.
    for i in range(1000):
        ts.record("tools", "event", float(i))  # støjende nerve, langt over maxlen
    ts.record("memory", "recall", 42.0)  # stille nerve, ét enkelt sample
    quiet = ts.recent("memory", "recall")
    assert len(quiet) == 1
    assert quiet[0].value == 42.0  # overlevede nabo-støjen


def test_maxlen_cap_per_nerve():
    for i in range(ts._PER_NERVE_MAX + 50):
        ts.record("c", "n", float(i))
    got = ts.recent("c", "n", limit=10_000)
    assert len(got) == ts._PER_NERVE_MAX  # cappet
    assert got[-1].value == float(ts._PER_NERVE_MAX + 49)  # nyeste bevaret


def test_recent_limit():
    for i in range(20):
        ts.record("c", "n", float(i))
    assert len(ts.recent("c", "n", limit=5)) == 5


def test_never_raises_on_bad_input():
    ts.record("", "", None)  # tom nøgle → no-op
    ts.record("c", "n", "not-a-number")  # type: ignore[arg-type]
    assert ts.recent("missing", "nerve") == []


def test_stats_and_nerves():
    ts.record("a", "1", 1.0)
    ts.record("b", "2", 1.0)
    st = ts.stats()
    assert st["nerve_count"] == 2
    assert st["total_samples"] == 2
    assert set(ts.nerves()) == {("a", "1"), ("b", "2")}
