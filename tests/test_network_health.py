"""Tests for core/services/network_health.py — samlet netværks-helbred (read-only, self-safe)."""
from __future__ import annotations

import pytest

from core.services import central_timeseries
from core.services import network_health as nh


@pytest.fixture(autouse=True)
def _clean():
    central_timeseries._reset_for_tests()
    nh._reset_for_tests()
    yield
    central_timeseries._reset_for_tests()
    nh._reset_for_tests()


def test_measure_api_latency_down_closed_port():
    # Port 1 på localhost er (næsten helt sikkert) lukket → ikke-oppe, ingen latens.
    ok, ms = nh.measure_api_latency(url="http://127.0.0.1:1/health", timeout=1.0)
    assert ok is False and ms is None


def test_hosts_down_reads_negative_reach_samples():
    central_timeseries.record("infra", "reach_pve", value=0.3, meta={"up": True})
    central_timeseries.record("infra", "reach_fileserver", value=-1.0, meta={"up": False})
    down = nh._hosts_down()
    assert "fileserver" in down and "pve" not in down


def _set_sample_age(nerve: str, value: float, age_s: float) -> None:
    """Skriv et sample med en bestemt alder (record() sætter altid ts til nu)."""
    from datetime import datetime, timedelta, timezone

    central_timeseries.record("infra", nerve, value=value)
    dq = central_timeseries._series[("infra", nerve)]
    old_ts = (datetime.now(timezone.utc) - timedelta(seconds=age_s)).isoformat()
    dq[-1] = central_timeseries.Sample(ts=old_ts, value=value)


def test_hosts_down_ignores_stale_negative_sample():
    # Målt 17/10-2026: ét transient probe-fejl skrev -1.0, og _hosts_down() læste det
    # som et vedvarende nedbrud — pfsense blev meldt «nede» mens den svarede 200.
    # Et sample ældre end _REACH_STALE_S beskriver ikke NU og må ikke tælle.
    _set_sample_age("reach_pfsense", -1.0, age_s=nh._REACH_STALE_S + 180)
    assert nh._hosts_down() == []


def test_hosts_down_keeps_fresh_negative_sample():
    # Frisk nede-sample SKAL stadig fanges — aldersgrænsen må ikke sløve ægte nedbrud.
    _set_sample_age("reach_pfsense", -1.0, age_s=60)
    assert nh._hosts_down() == ["pfsense"]


def test_tick_green_when_api_fast_and_all_up(monkeypatch):
    monkeypatch.setattr(nh, "measure_api_latency", lambda *a, **k: (True, 12.0))
    central_timeseries.record("infra", "reach_pve", value=0.2, meta={"up": True})
    central_timeseries.record("system", "provider_health_check", value=1.0)
    out = nh.run_network_health_tick()
    assert out["status"] == "green"
    # Ét fuset signal skal være skrevet.
    s = central_timeseries.recent("network", "health", limit=1)
    assert s and s[-1].value == 12.0 and s[-1].meta["status"] == "green"


def test_single_api_fail_is_yellow_not_red(monkeypatch):
    # Én fejlet probe (fx api-genstart-vindue) → gult transient, IKKE rødt flag.
    monkeypatch.setattr(nh, "measure_api_latency", lambda *a, **k: (False, None))
    out = nh.run_network_health_tick()
    assert out["status"] == "yellow" and out["api_fail_streak"] == 1


def test_api_down_red_only_after_streak(monkeypatch):
    monkeypatch.setattr(nh, "measure_api_latency", lambda *a, **k: (False, None))
    statuses = [nh.run_network_health_tick()["status"] for _ in range(nh._RED_STREAK)]
    # Først gul, gul, … så rød ved _RED_STREAK sammenhængende fejl.
    assert statuses[:-1] == ["yellow"] * (nh._RED_STREAK - 1)
    assert statuses[-1] == "red"


def test_api_recovers_resets_streak(monkeypatch):
    monkeypatch.setattr(nh, "measure_api_latency", lambda *a, **k: (False, None))
    nh.run_network_health_tick(); nh.run_network_health_tick()
    monkeypatch.setattr(nh, "measure_api_latency", lambda *a, **k: (True, 10.0))
    out = nh.run_network_health_tick()
    assert out["status"] == "green" and out["api_fail_streak"] == 0


def test_tick_red_when_critical_host_down(monkeypatch):
    monkeypatch.setattr(nh, "measure_api_latency", lambda *a, **k: (True, 20.0))
    central_timeseries.record("infra", "reach_pfsense", value=-1.0, meta={"up": False})
    out = nh.run_network_health_tick()
    assert out["status"] == "red" and "pfsense" in out["hosts_down"]


def test_tick_yellow_on_elevated_latency(monkeypatch):
    monkeypatch.setattr(nh, "measure_api_latency", lambda *a, **k: (True, 400.0))
    out = nh.run_network_health_tick()
    assert out["status"] == "yellow"


def test_tick_never_raises(monkeypatch):
    # Selv hvis alt fejler skal producer'en returnere pænt (bulletproof-kontrakt).
    monkeypatch.setattr(nh, "measure_api_latency", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    # measure_api_latency er selv self-safe i prod, men her verificerer vi at tick fanger.
    try:
        out = nh.run_network_health_tick()
    except Exception as e:  # pragma: no cover
        pytest.fail(f"tick kastede: {e}")
    assert isinstance(out, dict)
