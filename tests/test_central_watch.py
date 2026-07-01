"""Tests for core/services/central_watch.py — det aktive lag (flag+lær+notificér)."""
from __future__ import annotations

import pytest

from core.services import central_noise_filter, central_timeseries
from core.services import central_watch as cw


class _FakeCentral:
    def __init__(self):
        self.observed = []

    def observe(self, event):
        self.observed.append(dict(event))


@pytest.fixture(autouse=True)
def _clean():
    central_timeseries._reset_for_tests()
    central_noise_filter._reset_for_tests()
    yield
    central_timeseries._reset_for_tests()
    central_noise_filter._reset_for_tests()


@pytest.fixture
def wired(monkeypatch):
    central = _FakeCentral()
    incidents = []
    notifs = []
    monkeypatch.setattr(cw, "central", lambda: central)
    import core.runtime.db_central_incidents as dci
    monkeypatch.setattr(dci, "record_central_incident",
                        lambda **k: incidents.append(k) or 1)
    monkeypatch.setattr(cw, "_notify_owner",
                        lambda title, message, importance: notifs.append((importance, message)) or True)
    return central, incidents, notifs


# ── _raise_flag pipeline ──

def test_raise_flag_full_pipeline(wired):
    central, incidents, notifs = wired
    out = cw._raise_flag("system", "eventbus_bridge", severity="error",
                         message="bro fejlede", importance="high")
    assert out["incident"] is True and out["notified"] is True
    assert central.observed[0]["kind"] == "flag"
    assert len(incidents) == 1
    assert notifs == [("high", "bro fejlede")]
    assert len(central_timeseries.recent("system", "eventbus_bridge__flag")) == 1


def test_raise_flag_self_meta_makes_no_incident(wired):
    central, incidents, notifs = wired
    out = cw._raise_flag("system", "central_meta", severity="error",
                         message="drift", importance="high", make_incident=False)
    assert out["incident"] is False
    assert incidents == []  # §24.5: ingen selv-refererende lærings-incident
    assert out["notified"] is True  # men owner notificeres stadig


# ── run_watch_tick + støjfanger-integration ──

def test_bridge_failure_flags_only_after_persistence(wired):
    central, incidents, notifs = wired
    central_timeseries.record("system", "bridge_observe_failures", value=3.0)
    r1 = cw.run_watch_tick()
    assert r1["flag_count"] == 0  # ét tick = blip, støjfangeren holder igen
    r2 = cw.run_watch_tick()
    assert r2["flag_count"] == 1  # vedvarende → flag
    assert incidents and incidents[0]["nerve"] == "eventbus_bridge"
    assert notifs and notifs[0][0] == "high"


def test_central_meta_drift_flags_without_incident(wired):
    central, incidents, notifs = wired
    central_timeseries.record("system", "central_meta", value=500.0,
                              meta={"drift_ms": 500.0, "open_breakers": 0})
    cw.run_watch_tick()
    cw.run_watch_tick()
    # flagget kom (notificeret) men INGEN incident (§24.5 selv-meta)
    assert any(n[1].startswith("Centralens decide-latency") for n in notifs)
    assert incidents == []


def test_open_breakers_flag_critical(wired):
    central, incidents, notifs = wired
    central_timeseries.record("system", "central_meta", value=5.0,
                              meta={"drift_ms": 0.0, "open_breakers": 2})
    cw.run_watch_tick()
    cw.run_watch_tick()
    assert any(inc["nerve"] == "breaker" and inc["severity"] == "severe" for inc in incidents)
    assert any(n[0] == "critical" for n in notifs)


def test_inner_life_stall_flags_medium_no_push(wired):
    central, incidents, notifs = wired
    for _ in range(cw._INNER_SILENCE_MIN):
        central_timeseries.record("inner", "witness_daemon", value=0.0)
    cw.run_watch_tick()
    cw.run_watch_tick()
    # inner-stall fodrer læring (incident) men pusher IKKE owner (medium)
    assert any(inc["cluster"] == "inner" and inc["nerve"] == "witness_daemon" for inc in incidents)
    assert notifs == []


def test_cache_cold_flags_medium(wired):
    central, incidents, notifs = wired
    central_timeseries.record("cost", "prefix_cache", value=4.0,
                              meta={"prefix_sha": "abc", "lane": "visible"})
    cw.run_watch_tick()
    cw.run_watch_tick()
    # kold cache fodrer læring (incident) men pusher ikke owner (medium)
    assert any(inc["cluster"] == "cost" and inc["nerve"] == "prefix_cache" for inc in incidents)
    assert notifs == []


def test_warm_cache_no_flag(wired):
    central, incidents, notifs = wired
    central_timeseries.record("cost", "prefix_cache", value=85.0, meta={"prefix_sha": "abc"})
    cw.run_watch_tick()
    cw.run_watch_tick()
    assert not any(inc["nerve"] == "prefix_cache" for inc in incidents)


def test_healthy_streams_produce_no_flags(wired):
    central, incidents, notifs = wired
    central_timeseries.record("system", "bridge_observe_failures", value=0.0)
    central_timeseries.record("system", "central_meta", value=10.0,
                              meta={"drift_ms": 5.0, "open_breakers": 0})
    cw.run_watch_tick()
    cw.run_watch_tick()
    assert incidents == [] and notifs == []
