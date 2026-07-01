"""Tests for core/services/infra_sense.py — infra-sansning (read-only, self-safe)."""
from __future__ import annotations

import socket

import pytest

from core.services import central_timeseries
from core.services import infra_sense as isense


@pytest.fixture(autouse=True)
def _clean():
    central_timeseries._reset_for_tests()
    yield
    central_timeseries._reset_for_tests()


class _FakeCentral:
    def __init__(self):
        self.observed = []

    def observe(self, e):
        self.observed.append(dict(e))


def test_tcp_probe_down_closed_port():
    # port 1 på localhost er (næsten helt sikkert) lukket → nede, ingen latency
    up, lat = isense._tcp_probe("127.0.0.1", 1, timeout=1.0)
    assert up is False and lat is None


def test_tcp_probe_up_against_listener():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    port = srv.getsockname()[1]
    try:
        up, lat = isense._tcp_probe("127.0.0.1", port, timeout=1.0)
        assert up is True and isinstance(lat, float) and lat >= 0
    finally:
        srv.close()


def test_poll_reachability_observes_all_hosts(monkeypatch):
    central = _FakeCentral()
    monkeypatch.setattr(isense, "central", lambda: central)
    # alle hosts "oppe" med fast latency
    monkeypatch.setattr(isense, "_tcp_probe", lambda h, p, timeout=3.0: (True, 4.2))
    res = isense.poll_reachability()
    assert len(res) == len(isense.HOSTS)
    assert all(v["up"] for v in res.values())
    # observe pr. host + timeseries
    assert len(central.observed) == len(isense.HOSTS)
    assert all(o["cluster"] == "infra" and o["nerve"].startswith("reach_") for o in central.observed)
    assert central_timeseries.recent("infra", "reach_pve")[-1].value == 4.2


def test_poll_reachability_down_records_negative(monkeypatch):
    monkeypatch.setattr(isense, "central", lambda: _FakeCentral())
    monkeypatch.setattr(isense, "_tcp_probe", lambda h, p, timeout=3.0: (False, None))
    isense.poll_reachability()
    # nede → value=-1.0 (så central_watch kan flagge <0)
    assert central_timeseries.recent("infra", "reach_pfsense")[-1].value == -1.0


def test_poll_pihole_no_creds_is_safe(monkeypatch):
    import core.runtime.secrets as sec
    monkeypatch.setattr(sec, "read_runtime_key", lambda k: None)
    assert isense.poll_pihole() == {}  # ingen creds → tom, ingen crash


def test_tick_self_safe(monkeypatch):
    monkeypatch.setattr(isense, "poll_reachability", lambda: {"pve": {"up": True}})
    monkeypatch.setattr(isense, "poll_pihole", lambda: {"block_pct": 19.0})
    monkeypatch.setattr(isense, "poll_pfsense", lambda: {"uptime": "34d"})
    res = isense.run_infra_sense_tick()
    assert res["status"] == "ok" and res["hosts"] == 1


def test_tick_never_raises(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("net down")
    monkeypatch.setattr(isense, "poll_reachability", boom)
    # poll_reachability rejser, men run_infra_sense_tick kalder den udenfor try? — sikr self-safe:
    try:
        isense.run_infra_sense_tick()
    except Exception:
        pytest.fail("run_infra_sense_tick må ikke kaste")
