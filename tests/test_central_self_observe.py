"""Tests for core/services/central_self_observe.py — Fase 1 selv-observation (§24.5)."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from core.services import central_self_observe as so
from core.services import central_timeseries


def _rec(kind, latency_ms=0, decision=""):
    return SimpleNamespace(kind=kind, latency_ms=latency_ms, decision=decision)


class _FakeSink:
    def __init__(self, records, dropped=0):
        self._records = records
        self.dropped = dropped

    def recent(self, limit=500):
        return list(self._records[-limit:])


class _FakeCentral:
    def __init__(self, open_breakers=None):
        self.observed = []
        self.decided = []
        self._breaker = SimpleNamespace(open_nerves=lambda: list(open_breakers or []))

    def observe(self, event):
        self.observed.append(dict(event))

    def decide(self, *a, **k):  # må ALDRIG kaldes af selv-observationen (§24.5)
        self.decided.append((a, k))


class _FakeCache:
    def __init__(self):
        self.store = {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value, *, ttl_seconds):
        self.store[key] = value


@pytest.fixture(autouse=True)
def _clean():
    central_timeseries._reset_for_tests()
    yield
    central_timeseries._reset_for_tests()


@pytest.fixture
def wired(monkeypatch):
    central = _FakeCentral(open_breakers=["nerve_x"])
    cache = _FakeCache()
    monkeypatch.setattr(so, "central", lambda: central)
    monkeypatch.setattr(so, "shared_cache", cache)

    def _bind_trace(records, dropped=0):
        monkeypatch.setattr(so.central_trace, "sink", lambda: _FakeSink(records, dropped))

    return central, cache, _bind_trace


def test_percentile():
    assert so._percentile([], 0.5) == 0.0
    assert so._percentile([5.0], 0.95) == 5.0
    assert so._percentile([1.0, 2.0, 3.0, 4.0], 0.5) == 2.5
    assert so._percentile([1.0, 2.0, 3.0, 4.0], 1.0) == 4.0


def test_sample_metrics_counts_and_latency(wired):
    central, cache, bind_trace = wired
    bind_trace([
        _rec("decide", 10, "green"),
        _rec("decide", 20, "red"),
        _rec("decide", 30, "green"),
        _rec("observe"),
        _rec("error"),
    ])
    m = so.sample_self_metrics()
    assert m["decide_count"] == 3
    assert m["observe_count"] == 1
    assert m["error_count"] == 1
    assert m["red_count"] == 1
    assert m["open_breakers"] == 1
    assert m["max_ms"] == 30.0
    assert m["p50_ms"] == 20.0


def test_baseline_first_time_no_drift(wired):
    central, cache, bind_trace = wired
    bind_trace([_rec("decide", 100, "green")])
    m = so.sample_self_metrics()
    assert m["latency_drift_ms"] == 0.0  # første gang → ingen drift
    assert cache.store.get(so._BASELINE_KEY) is not None  # baseline sat


def test_outlier_clipping_protects_baseline(wired):
    central, cache, bind_trace = wired
    cache.store[so._BASELINE_KEY] = {"p95": 10.0}  # etableret lav baseline
    bind_trace([_rec("decide", 10_000, "green")])  # voldsom spike
    m = so.sample_self_metrics()
    # Drift RAPPORTERES fuldt (spike er synlig)...
    assert m["latency_drift_ms"] > 9000
    # ...men baseline er clippet, så én spike ikke forgifter den.
    new_baseline = cache.store[so._BASELINE_KEY]["p95"]
    assert new_baseline < 50.0  # ~16, ikke ~2000


def test_tick_observes_and_is_trigger_free(wired):
    central, cache, bind_trace = wired
    bind_trace([_rec("decide", 15, "green"), _rec("observe")])
    res = so.run_self_observe_tick()
    assert res["status"] == "ok"
    # observed til system/central_meta
    assert len(central.observed) == 1
    ev = central.observed[0]
    assert (ev["cluster"], ev["nerve"], ev["kind"]) == ("system", "central_meta", "observe")
    # UDLØSER-FRI (§24.5): decide må ALDRIG kaldes af selv-observationen
    assert central.decided == []
    # tidsserie fik et sample
    assert len(central_timeseries.recent("system", "central_meta")) == 1


def test_never_raises_on_broken_sink(wired, monkeypatch):
    central, cache, bind_trace = wired
    monkeypatch.setattr(so.central_trace, "sink", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    m = so.sample_self_metrics()  # må ikke kaste
    assert m["decide_count"] == 0
    res = so.run_self_observe_tick()  # må ikke kaste
    assert res["status"] == "ok"
