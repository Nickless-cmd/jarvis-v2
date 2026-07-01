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
    # Stub cross-proces-læsere til sunde defaults → tests deterministiske; enkelt-tests overrider.
    monkeypatch.setattr(cw, "_recent_cache_pcts", lambda limit=6: [])
    monkeypatch.setattr(cw, "_tool_outcome_counts", lambda limit=40: (0, 0))
    monkeypatch.setattr(cw, "_heed_summary", lambda: {})
    monkeypatch.setattr(cw, "_today_cost_usd", lambda: None)
    monkeypatch.setattr(cw, "_cheap_lane_stats", lambda limit=40: (0, 0))
    monkeypatch.setattr(cw, "_council_forced_count", lambda limit=40: 0)
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


def test_cache_cold_flags_medium(wired, monkeypatch):
    central, incidents, notifs = wired
    # cache læses cross-proces fra eventbus; selv de varmeste kald er kolde → flag
    monkeypatch.setattr(cw, "_recent_cache_pcts", lambda limit=6: [4.0, 3.0, 5.0])
    cw.run_watch_tick()
    cw.run_watch_tick()
    # kold cache fodrer læring (incident) men pusher ikke owner (medium)
    assert any(inc["cluster"] == "cost" and inc["nerve"] == "prefix_cache" for inc in incidents)
    assert notifs == []


def test_warm_cache_no_flag(wired, monkeypatch):
    central, incidents, notifs = wired
    # første-kald-miss (13%) er normalt så længe varme kald hitter (83%) → INGEN flag
    monkeypatch.setattr(cw, "_recent_cache_pcts", lambda limit=6: [13.0, 83.0, 13.0])
    cw.run_watch_tick()
    cw.run_watch_tick()
    assert not any(inc["nerve"] == "prefix_cache" for inc in incidents)


def test_recall_never_creates_incident(wired):
    # Rettet 1. jul: recall-tom er NORMALT (berigelse), aldrig et incident (var false-positive).
    central, incidents, notifs = wired
    cw.run_watch_tick()
    cw.run_watch_tick()
    assert not any(inc["nerve"] == "recall" for inc in incidents)


def test_tool_error_rate_flags_high(wired, monkeypatch):
    central, incidents, notifs = wired
    monkeypatch.setattr(cw, "_tool_outcome_counts", lambda limit=40: (20, 10))  # 50%
    monkeypatch.setattr(cw, "_heed_summary", lambda: {})
    cw.run_watch_tick()
    cw.run_watch_tick()
    assert any(inc["cluster"] == "tools" and inc["nerve"] == "outcome" for inc in incidents)
    assert any(n[0] == "high" for n in notifs)


def test_tool_low_error_no_flag(wired, monkeypatch):
    central, incidents, notifs = wired
    monkeypatch.setattr(cw, "_tool_outcome_counts", lambda limit=40: (20, 1))  # 5%
    monkeypatch.setattr(cw, "_heed_summary", lambda: {})
    cw.run_watch_tick()
    cw.run_watch_tick()
    assert not any(inc["nerve"] == "outcome" for inc in incidents)


def test_heed_low_observed_but_no_incident(wired, monkeypatch):
    # Rettet 1. jul: heed_rate er langsom steady-state kvalitetsmetrik → observe/trend, ALDRIG
    # incident (var false-positive der farvede Centralen rød).
    central, incidents, notifs = wired
    monkeypatch.setattr(cw, "_tool_outcome_counts", lambda limit=40: (0, 0))
    monkeypatch.setattr(cw, "_heed_summary",
                        lambda: {"surfaced_total": 10, "strict_heed_rate": 0.2})
    cw.run_watch_tick()
    cw.run_watch_tick()
    # observeret (synlig/trendbar) men INGEN incident
    assert any(o.get("nerve") == "verification_heed" for o in central.observed)
    assert not any(inc["nerve"] == "verification_heed" for inc in incidents)


def test_cheap_lane_failover_flags(wired, monkeypatch):
    central, incidents, notifs = wired
    monkeypatch.setattr(cw, "_cheap_lane_stats", lambda limit=40: (2, 8))  # 80% fejl
    cw.run_watch_tick()
    cw.run_watch_tick()
    assert any(inc["cluster"] == "cost" and inc["nerve"] == "cheap_lane" for inc in incidents)


def test_cheap_lane_healthy_no_flag(wired, monkeypatch):
    central, incidents, notifs = wired
    monkeypatch.setattr(cw, "_cheap_lane_stats", lambda limit=40: (9, 1))  # 10% fejl
    cw.run_watch_tick()
    cw.run_watch_tick()
    assert not any(inc["nerve"] == "cheap_lane" for inc in incidents)


def test_cost_observed_each_tick(wired, monkeypatch):
    central, incidents, notifs = wired
    monkeypatch.setattr(cw, "_today_cost_usd", lambda: 1.23)
    cw.run_watch_tick()
    assert any(o.get("nerve") == "ledger" and o.get("usd_today") == 1.23 for o in central.observed)


def test_council_deadlock_flags(wired, monkeypatch):
    central, incidents, notifs = wired
    monkeypatch.setattr(cw, "_council_forced_count", lambda limit=40: 4)
    cw.run_watch_tick()
    cw.run_watch_tick()
    assert any(inc["cluster"] == "agents" and inc["nerve"] == "council" for inc in incidents)


def test_council_healthy_no_flag(wired, monkeypatch):
    central, incidents, notifs = wired
    monkeypatch.setattr(cw, "_council_forced_count", lambda limit=40: 1)
    cw.run_watch_tick()
    cw.run_watch_tick()
    assert not any(inc["nerve"] == "council" for inc in incidents)


def test_infra_host_down_flags_high(wired):
    central, incidents, notifs = wired
    # host nede 2 tick i træk (value=-1) → flag high + push
    for _ in range(2):
        central_timeseries.record("infra", "reach_fileserver", value=-1.0,
                                  meta={"target": "10.0.0.10:22"})
    cw.run_watch_tick()
    cw.run_watch_tick()
    assert any(inc["cluster"] == "infra" and inc["nerve"] == "reach_fileserver" for inc in incidents)
    assert any(n[0] == "high" for n in notifs)


def test_infra_host_up_no_flag(wired):
    central, incidents, notifs = wired
    for _ in range(2):
        central_timeseries.record("infra", "reach_pve", value=3.5, meta={"target": "10.0.0.2:22"})
    cw.run_watch_tick()
    cw.run_watch_tick()
    assert not any(inc["nerve"] == "reach_pve" for inc in incidents)


def test_infra_disk_high_flags(wired):
    central, incidents, notifs = wired
    central_timeseries.record("infra", "fileserver_disk", value=94.0)
    central_timeseries.record("infra", "fileserver_disk", value=95.0)
    cw.run_watch_tick()
    cw.run_watch_tick()
    assert any(inc["cluster"] == "infra" and inc["nerve"] == "fileserver_disk" for inc in incidents)


def test_infra_svc_down_flags(wired):
    central, incidents, notifs = wired
    central_timeseries.record("infra", "webservice_svc_down", value=2.0)
    central_timeseries.record("infra", "webservice_svc_down", value=2.0)
    cw.run_watch_tick()
    cw.run_watch_tick()
    assert any(inc["nerve"] == "webservice_svc_down" for inc in incidents)


def test_infra_disk_ok_no_flag(wired):
    central, incidents, notifs = wired
    central_timeseries.record("infra", "pve_disk", value=45.0)
    central_timeseries.record("infra", "pve_disk", value=46.0)
    cw.run_watch_tick()
    cw.run_watch_tick()
    assert not any(inc["nerve"] == "pve_disk" for inc in incidents)


def test_healthy_streams_produce_no_flags(wired):
    central, incidents, notifs = wired
    central_timeseries.record("system", "bridge_observe_failures", value=0.0)
    central_timeseries.record("system", "central_meta", value=10.0,
                              meta={"drift_ms": 5.0, "open_breakers": 0})
    cw.run_watch_tick()
    cw.run_watch_tick()
    assert incidents == [] and notifs == []
