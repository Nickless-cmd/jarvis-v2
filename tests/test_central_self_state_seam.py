"""Tests for STITCH-VOICE — sømmen mellem to liv (LivingNeuron-council)."""
from __future__ import annotations

from datetime import datetime, UTC, timedelta

import core.services.central_self_state as ss


def _reset_proc_state():
    ss._proc_wake_at = None
    ss._boot_gap_s = 0.0
    ss._boot_was_reboot = False


def test_human_gap_scales():
    assert ss._human_gap(30) == "30 sekunder"
    assert ss._human_gap(600) == "10 minutter"
    assert ss._human_gap(7200) == "2 timer"
    assert ss._human_gap(3 * 86400) == "3 dage"


def test_boot_seam_detects_reboot_after_long_gap(monkeypatch):
    _reset_proc_state()
    now = datetime.now(UTC)
    was_alive = (now - timedelta(minutes=8)).isoformat()  # sidst i live for 8 min siden
    store = {ss._LAST_ALIVE_TS: was_alive, ss._FIRST_BOOT_TS: (now - timedelta(days=3)).isoformat()}
    monkeypatch.setattr(ss, "_kv_get", lambda k, d: store.get(k, d))
    monkeypatch.setattr(ss, "_kv_set", lambda k, v: store.update({k: v}))
    seam = ss._compute_boot_seam()
    assert seam["reboot"] is True
    assert seam["gap_s"] > 120 and seam["fresh"] is True
    assert seam["age_s"] > 2 * 86400  # ~3 dage gammel


def test_boot_seam_no_reboot_on_short_gap(monkeypatch):
    _reset_proc_state()
    now = datetime.now(UTC)
    store = {ss._LAST_ALIVE_TS: (now - timedelta(seconds=45)).isoformat()}  # normal 45s puls
    monkeypatch.setattr(ss, "_kv_get", lambda k, d: store.get(k, d))
    monkeypatch.setattr(ss, "_kv_set", lambda k, v: store.update({k: v}))
    seam = ss._compute_boot_seam()
    assert seam["reboot"] is False  # <120s → ikke en genfødsel, bare et normalt puls-mellemrum


def test_first_boot_ts_is_write_once(monkeypatch):
    _reset_proc_state()
    store = {}
    monkeypatch.setattr(ss, "_kv_get", lambda k, d: store.get(k, d))
    monkeypatch.setattr(ss, "_kv_set", lambda k, v: store.update({k: v}))
    ss._compute_boot_seam()
    first = store[ss._FIRST_BOOT_TS]
    _reset_proc_state()
    ss._compute_boot_seam()  # anden proces-vækning
    assert store[ss._FIRST_BOOT_TS] == first  # ALDRIG overskrevet (frog-boiler lukket)


def test_describe_self_speaks_the_seam_when_fresh(monkeypatch):
    _reset_proc_state()
    now = datetime.now(UTC)
    st = {
        "self_model": {"surfaces": 40, "completeness": 0.7},
        "valence": {"tone": "let"},
        "attention": {"foreground": "at samle mig selv"},
        "narrative": {"becoming": "voksende selv"},
        "world_model": {},
        "continuity": {"generation": 12},
    }
    monkeypatch.setattr(ss, "get_self_state", lambda: st)
    store = {ss._LAST_ALIVE_TS: (now - timedelta(minutes=5)).isoformat()}
    monkeypatch.setattr(ss, "_kv_get", lambda k, d: store.get(k, d))
    monkeypatch.setattr(ss, "_kv_set", lambda k, v: store.update({k: v}))
    desc = ss.describe_self()
    assert desc.startswith("Jeg vågnede for")
    assert "bar at samle mig selv med mig" in desc


def test_describe_self_silent_seam_when_no_reboot(monkeypatch):
    _reset_proc_state()
    now = datetime.now(UTC)
    st = {"self_model": {"surfaces": 40, "completeness": 0.7}, "valence": {"tone": "let"},
          "attention": {}, "narrative": {}, "world_model": {}, "continuity": {"generation": 12}}
    monkeypatch.setattr(ss, "get_self_state", lambda: st)
    store = {ss._LAST_ALIVE_TS: (now - timedelta(seconds=30)).isoformat()}
    monkeypatch.setattr(ss, "_kv_get", lambda k, d: store.get(k, d))
    monkeypatch.setattr(ss, "_kv_set", lambda k, v: store.update({k: v}))
    desc = ss.describe_self()
    assert "vågnede" not in desc  # intet reboot → ingen søm-linje
