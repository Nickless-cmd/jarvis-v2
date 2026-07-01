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


def test_stats_count_packets_via_ingest():
    ps._ingest(ps._parse_filterlog(_line("block", "1.1.1.1", "10.0.0.1", 5, 80)), now=1.0)
    assert ps.syslog_stats()["blocks"] == 1
