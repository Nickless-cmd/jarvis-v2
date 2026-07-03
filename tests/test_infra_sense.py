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


def test_parse_kv():
    kv = isense._parse_kv("disk=87 svc_down=0 smb=active")
    assert kv == {"disk": 87, "svc_down": 0, "smb": "active"}


def test_poll_ssh_hosts_observes(monkeypatch):
    central = _FakeCentral()
    monkeypatch.setattr(isense, "central", lambda: central)
    fake = {"root@10.0.0.2": "guests_running=6 guests_total=6 maxdisk=45 load1=1.8",
            "root@192.168.50.32": "disk=19 svc_down=0",
            "root@10.0.0.10": "disk=24 smb=active"}
    monkeypatch.setattr(isense, "_ssh_run", lambda t, c, timeout=8.0: fake.get(t))
    res = isense.poll_ssh_hosts()
    assert res["pve"]["guests_running"] == 6
    assert res["webservice"]["svc_down"] == 0
    # observe pr. host + disk-tidsserie
    assert any(o["nerve"] == "pve_health" for o in central.observed)
    assert central_timeseries.recent("infra", "pve_disk")[-1].value == 45.0
    assert central_timeseries.recent("infra", "webservice_svc_down")[-1].value == 0.0


def test_poll_ssh_hosts_down_host_skipped(monkeypatch):
    monkeypatch.setattr(isense, "central", lambda: _FakeCentral())
    monkeypatch.setattr(isense, "_ssh_run", lambda t, c, timeout=8.0: None)  # alle nede
    assert isense.poll_ssh_hosts() == {}  # ingen crash, ingen data


def test_poll_ha_observes(monkeypatch):
    central = _FakeCentral()
    monkeypatch.setattr(isense, "central", lambda: central)
    import core.runtime.secrets as sec
    monkeypatch.setattr(sec, "read_runtime_key", lambda k: "ha-token")
    states = [{"entity_id": "person.bjorn", "state": "home"},
              {"entity_id": "sensor.temp", "state": "21.5"},
              {"entity_id": "light.stue", "state": "unavailable"}]
    monkeypatch.setattr(isense, "_http_json", lambda *a, **k: states)
    out = isense.poll_ha()
    assert out["persons_home"] == 1 and out["unavailable"] == 1 and out["entities"] == 3
    assert central_timeseries.recent("infra", "ha_unavailable")[-1].value == 1.0


def test_tick_never_raises(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("net down")
    monkeypatch.setattr(isense, "poll_reachability", boom)
    # poll_reachability rejser, men run_infra_sense_tick kalder den udenfor try? — sikr self-safe:
    try:
        isense.run_infra_sense_tick()
    except Exception:
        pytest.fail("run_infra_sense_tick må ikke kaste")


def _patch_syslog(monkeypatch, *, packets, last_packet_epoch, alive=None, detections=None):
    """Fælles opsætning: mock pfSense-syslog-modulet + central + notifikation + proces-tjek.
    alive = hvad _pfsense_syslogd_running() returnerer (True/False/None)."""
    from core.services import pfsense_syslog
    from core.runtime import db_central_incidents
    monkeypatch.setattr(pfsense_syslog, "drain_detections", lambda: list(detections or []))
    monkeypatch.setattr(pfsense_syslog, "syslog_stats",
                        lambda: {"packets": packets, "blocks": 0, "detections": 0,
                                 "last_packet_epoch": last_packet_epoch})
    monkeypatch.setattr(isense, "central", lambda: _FakeCentral())
    checks: list = []
    def _fake_alive():
        checks.append(True)
        return alive
    monkeypatch.setattr(isense, "_pfsense_syslogd_running", _fake_alive)
    notes: list = []
    monkeypatch.setattr(isense, "_notify_owner_security", lambda t, m: notes.append((t, m)))
    incidents: list = []
    monkeypatch.setattr(db_central_incidents, "record_central_incident",
                        lambda **kw: incidents.append(kw))
    isense._syslog_stale_flagged = False
    isense._syslogd_check_counter = 0
    return incidents, notes, checks


def _prime_counter():
    # Sæt tælleren så NÆSTE stille tick udløser det aktive proces-tjek.
    isense._syslogd_check_counter = isense._SYSLOGD_CHECK_EVERY - 1


def test_syslog_flags_when_process_confirmed_dead(monkeypatch):
    # Vedvarende tavshed + aktivt tjek bekræfter død proces → flag + notifikation.
    incidents, notes, checks = _patch_syslog(monkeypatch, packets=611, last_packet_epoch=0.0, alive=False)
    _prime_counter()
    isense.poll_syslog()
    assert checks  # aktivt proces-tjek blev kørt
    assert any(i.get("kind") == "syslogd_dead" for i in incidents)
    assert notes and isense._syslog_stale_flagged is True


def test_syslog_quiet_but_alive_no_flag(monkeypatch):
    # Stille (CGNAT-nat) MEN processen lever → INGEN falsk alarm.
    incidents, notes, checks = _patch_syslog(monkeypatch, packets=611, last_packet_epoch=0.0, alive=True)
    _prime_counter()
    isense.poll_syslog()
    assert checks  # tjek kørt
    assert not any(i.get("kind") == "syslogd_dead" for i in incidents)
    assert not notes and isense._syslog_stale_flagged is False


def test_syslog_flowing_skips_active_check(monkeypatch):
    # Pakker flyder (frisk) → syslogd åbenlyst i live → INTET aktivt tjek, tæller nulstilles.
    import time
    incidents, _n, checks = _patch_syslog(monkeypatch, packets=611, last_packet_epoch=time.time() - 5, alive=False)
    _prime_counter()
    isense.poll_syslog()
    assert not checks  # intet aktivt tjek når pakker flyder
    assert not any(i.get("kind") == "syslogd_dead" for i in incidents)
    assert isense._syslogd_check_counter == 0


def test_syslog_silent_but_not_yet_threshold_no_check(monkeypatch):
    # Stille men tælleren ikke nået tærskel endnu → intet tjek (throttle).
    incidents, _n, checks = _patch_syslog(monkeypatch, packets=611, last_packet_epoch=0.0, alive=False)
    isense._syslogd_check_counter = 0  # langt fra tærskel
    isense.poll_syslog()
    assert not checks and not incidents


def test_syslog_flag_clears_on_resume(monkeypatch):
    import time
    incidents, _n, _c = _patch_syslog(monkeypatch, packets=700, last_packet_epoch=time.time() - 5, alive=True)
    isense._syslog_stale_flagged = True  # var flagget → pakker flyder nu → skal ryddes
    isense.poll_syslog()
    assert isense._syslog_stale_flagged is False
