"""Tests for core/services/pfsense_syslog.py — pfSense-syslog-detektion (read-only)."""
from __future__ import annotations

import pytest

from core.services import pfsense_syslog as ps


@pytest.fixture(autouse=True)
def _clean():
    ps._reset_for_tests()
    yield
    ps._reset_for_tests()


def _line(action, src, dst, sport, dport):
    # realistisk pfSense filterlog-CSV (IPv4 TCP)
    return (f"<134>filterlog[123]: 5,,,1000103,em0,match,{action},in,4,0x0,,64,111,0,DF,6,tcp,60,"
            f"{src},{dst},{sport},{dport},0,S,,,,,")


def test_parse_filterlog_extracts_dstport():
    r = ps._parse_filterlog(_line("block", "1.2.3.4", "10.0.0.1", 44321, 22))
    assert r == {"action": "block", "src": "1.2.3.4", "dst": "10.0.0.1", "dport": 22}


def test_parse_non_filterlog_ignored():
    assert ps._parse_filterlog("<13>some other syslog line") is None


def test_pass_not_aggregated():
    ps._ingest(ps._parse_filterlog(_line("pass", "1.2.3.4", "10.0.0.1", 5, 80)), now=1.0)
    assert ps.syslog_stats()["blocks"] == 0
    assert ps.drain_detections() == []


def test_port_scan_detected():
    # én IP → mange distinkte dst-porte = port-scan
    for port in range(1, ps._SCAN_PORTS + 2):
        ps._ingest(ps._parse_filterlog(_line("block", "9.9.9.9", "10.0.0.1", 1000, port)), now=1.0)
    dets = ps.drain_detections()
    assert any(d["kind"] == "port_scan" and d["src"] == "9.9.9.9" for d in dets)


def test_brute_force_detected():
    # én IP → mange blokke mod SAMME port = brute-force
    for i in range(ps._BRUTE_BLOCKS + 1):
        ps._ingest(ps._parse_filterlog(_line("block", "8.8.8.8", "10.0.0.1", 2000 + i, 22)), now=1.0)
    dets = ps.drain_detections()
    assert any(d["kind"] == "brute_force" and d["src"] == "8.8.8.8" for d in dets)


def test_drain_clears():
    for port in range(1, ps._SCAN_PORTS + 2):
        ps._ingest(ps._parse_filterlog(_line("block", "7.7.7.7", "10.0.0.1", 1000, port)), now=1.0)
    assert len(ps.drain_detections()) >= 1
    assert ps.drain_detections() == []  # ryddet


def test_cooldown_dedup():
    # samme IP scanner igen inden for cooldown → ingen NY detektion
    def scan(t):
        for port in range(1, ps._SCAN_PORTS + 2):
            ps._ingest(ps._parse_filterlog(_line("block", "6.6.6.6", "10.0.0.1", 1000, port)), now=t)
    scan(1.0)
    assert len(ps.drain_detections()) == 1
    scan(2.0)  # inden for cooldown
    assert ps.drain_detections() == []


def test_multicast_broadcast_excluded():
    # multicast (mDNS 224.0.0.251) + broadcast = normal støj, ikke brute-force
    for i in range(ps._BRUTE_BLOCKS + 5):
        ps._ingest(ps._parse_filterlog(_line("block", "100.75.136.21", "224.0.0.251", 5353, 5353)), now=1.0)
    for i in range(ps._BRUTE_BLOCKS + 5):
        ps._ingest(ps._parse_filterlog(_line("block", "10.0.0.9", "10.0.0.255", 138, 138)), now=1.0)
    assert ps.drain_detections() == []  # ingen false-positive
    assert ps._is_noise_dst("239.255.255.250") is True   # SSDP multicast
    assert ps._is_noise_dst("8.8.8.8") is False          # unicast = ægte


def test_unicast_brute_force_still_detected():
    # ægte: unicast-host, mange blokke → stadig fanget
    for i in range(ps._BRUTE_BLOCKS + 1):
        ps._ingest(ps._parse_filterlog(_line("block", "45.1.2.3", "10.0.0.1", 2000 + i, 22)), now=1.0)
    assert any(d["kind"] == "brute_force" for d in ps.drain_detections())


def test_stats_count_packets_via_ingest():
    ps._ingest(ps._parse_filterlog(_line("block", "1.1.1.1", "10.0.0.1", 5, 80)), now=1.0)
    assert ps.syslog_stats()["blocks"] == 1


def test_is_internal_src():
    assert ps._is_internal_src("192.168.50.84") is True   # CheifOne
    assert ps._is_internal_src("10.0.0.39") is True        # Jarvis-container
    assert ps._is_internal_src("172.16.5.5") is True
    assert ps._is_internal_src("127.0.0.1") is True
    assert ps._is_internal_src("185.107.14.241") is False  # ekstern scanner
    assert ps._is_internal_src("8.8.8.8") is False


def test_internal_source_not_detected_as_bruteforce():
    # Husets egen maskine (192.168.50.84=CheifOne) laver 30+ spærrede udgående → IKKE detektion.
    for i in range(ps._BRUTE_BLOCKS + 5):
        ps._ingest(ps._parse_filterlog(_line("block", "192.168.50.84", "216.239.34.223", 3000 + i, 443)), now=1.0)
    assert ps.drain_detections() == []          # ingen false-positive brute_force
    assert ps.syslog_stats()["blocks"] >= ps._BRUTE_BLOCKS  # blokke tælles stadig (stats)


def test_internal_source_not_detected_as_portscan():
    for port in range(1, ps._SCAN_PORTS + 2):
        ps._ingest(ps._parse_filterlog(_line("block", "10.0.0.55", "8.8.8.8", 1000, port)), now=1.0)
    assert ps.drain_detections() == []          # intern port-scan-mønster = ikke angreb


# ---------------------------------------------------------------------------
# Bjørn fik 3/9 en notifikation: «brute_force fra 185.107.14.241» — hans EGEN
# offentlige adresse. Og «204.76.203.231» fem gange i træk om noget der
# allerede var blokeret permanent.
# ---------------------------------------------------------------------------

def _block(src, dport, dst="100.75.136.21"):
    return {"action": "block", "src": src, "dst": dst, "dport": dport}


def test_cgnat_source_is_not_an_attacker(monkeypatch):
    """Vores WAN sidder SELV i CGNAT-rummet, og pfSense' regel om private
    netværk logger hver eneste pakke derfra. Uden denne grænse bliver
    ISP-segmentets almindelige støj til en strøm af trussels-alarmer."""
    import core.services.pfsense_syslog as m

    m._reset_for_tests()
    for p in range(60):
        m._ingest(_block("100.75.136.21", p), 1000.0)
    assert m.drain_detections() == []


def test_own_public_ip_is_not_an_attacker(monkeypatch):
    """En blok med os selv som kilde er vores egen trafik gennem vores egen
    firewall — ikke et angreb mod os."""
    import core.services.pfsense_syslog as m

    monkeypatch.setattr(m, "_self_ips", lambda: {"185.107.14.241"})
    m._reset_for_tests()
    for p in range(60):
        m._ingest(_block("185.107.14.241", p), 1000.0)
    assert m.drain_detections() == []

    # En fremmed på samme mønster SKAL stadig fanges — vagten må ikke gøre
    # detektoren blind.
    m._reset_for_tests()
    for p in range(60):
        m._ingest(_block("203.0.113.9", p), 1000.0)
    assert [d["src"] for d in m.drain_detections()] == ["203.0.113.9"]


def test_repeat_alerts_back_off_instead_of_repeating_every_ten_minutes():
    """En scanner der er blokeret bliver ved i timevis. Med fast dedup gav den
    seks beskeder i timen om noget der allerede virker som det skal."""
    import core.services.pfsense_syslog as m

    m._reset_for_tests()
    t = 1000.0
    fired = []
    for _ in range(4):
        for p in range(20):
            m._ingest(_block("198.51.100.7", p), t)
        got = m.drain_detections()
        if got:
            fired.append(t)
        t += m._DETECT_COOLDOWN_S + 1.0     # lige over den FØRSTE ventetid

    # Første alarm kommer straks. De næste gør ikke, fordi ventetiden vokser.
    assert len(fired) == 1, f"forventede én alarm, fik {len(fired)}"

    # Men den er ikke tavs for evigt — efter den voksede ventetid melder den igen.
    for p in range(20):
        m._ingest(_block("198.51.100.7", p), t + m._COOLDOWN_MAX_S)
    assert [d["src"] for d in m.drain_detections()] == ["198.51.100.7"]


def test_self_ips_survives_the_string_repr_of_a_json_list(monkeypatch):
    """read_runtime_key kører altid str() på værdien, så en JSON-liste kommer
    tilbage som sin repr. Et naivt split på komma gav "['185.107.14.241'" —
    og så genkendte vi IKKE vores egen adresse, hvilket var hele pointen."""
    import core.services.pfsense_syslog as m
    import core.runtime.secrets as secrets

    monkeypatch.setattr(
        secrets, "read_runtime_key",
        lambda *a, **k: "['185.107.14.241', '100.75.136.21']",
    )
    assert m._self_ips() == {"185.107.14.241", "100.75.136.21"}
    assert m._is_internal_src("185.107.14.241") is True
    assert m._is_internal_src("203.0.113.9") is False


def test_self_ips_also_accepts_a_plain_comma_list(monkeypatch):
    import core.services.pfsense_syslog as m
    import core.runtime.secrets as secrets

    monkeypatch.setattr(secrets, "read_runtime_key", lambda *a, **k: "1.2.3.4, 5.6.7.8")
    assert m._self_ips() == {"1.2.3.4", "5.6.7.8"}
