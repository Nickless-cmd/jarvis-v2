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
