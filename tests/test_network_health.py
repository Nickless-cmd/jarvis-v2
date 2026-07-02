"""Tests for core/services/network_health.py — samlet netværks-helbred (read-only, self-safe)."""
from __future__ import annotations

import pytest

from core.services import central_timeseries
from core.services import network_health as nh


@pytest.fixture(autouse=True)
def _clean():
    central_timeseries._reset_for_tests()
    yield
    central_timeseries._reset_for_tests()


def test_measure_api_latency_down_closed_port():
    # Port 1 på localhost er (næsten helt sikkert) lukket → ikke-oppe, ingen latens.
    ok, ms = nh.measure_api_latency(url="http://127.0.0.1:1/health", timeout=1.0)
    assert ok is False and ms is None


def test_hosts_down_reads_negative_reach_samples():
    central_timeseries.record("infra", "reach_pve", value=0.3, meta={"up": True})
    central_timeseries.record("infra", "reach_fileserver", value=-1.0, meta={"up": False})
    down = nh._hosts_down()
    assert "fileserver" in down and "pve" not in down


def test_tick_green_when_api_fast_and_all_up(monkeypatch):
    monkeypatch.setattr(nh, "measure_api_latency", lambda *a, **k: (True, 12.0))
    central_timeseries.record("infra", "reach_pve", value=0.2, meta={"up": True})
    central_timeseries.record("system", "provider_health_check", value=1.0)
    out = nh.run_network_health_tick()
    assert out["status"] == "green"
    # Ét fuset signal skal være skrevet.
    s = central_timeseries.recent("network", "health", limit=1)
    assert s and s[-1].value == 12.0 and s[-1].meta["status"] == "green"


def test_tick_red_when_api_down(monkeypatch):
    monkeypatch.setattr(nh, "measure_api_latency", lambda *a, **k: (False, None))
    out = nh.run_network_health_tick()
    assert out["status"] == "red" and out["api_ok"] is False


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
