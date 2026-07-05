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


def test_boot_seam_writes_latch_on_real_reboot(monkeypatch):
    """Ægte reboot (gap>120s) → latchen skrives durabelt, så en senere-bootende proces
    kan adoptere den selv om dens egen puls er blevet klobbet."""
    _reset_proc_state()
    now = datetime.now(UTC)
    store = {ss._LAST_ALIVE_TS: (now - timedelta(minutes=44)).isoformat()}
    monkeypatch.setattr(ss, "_kv_get", lambda k, d: store.get(k, d))
    monkeypatch.setattr(ss, "_kv_set", lambda k, v: store.update({k: v}))
    seam = ss._compute_boot_seam()
    assert seam["reboot"] is True and seam["gap_s"] > 2400
    latch = store.get(ss._SEAM_LATCH)
    assert latch and latch["reboot"] is True and latch["gap_s"] > 2400


def test_boot_seam_adopts_fresh_reboot_latch_when_pulse_clobbered(monkeypatch):
    """Cross-proces (rod-årsagen): vores egen puls ser frisk ud (30s) fordi proces #1's
    boot-puls allerede klobbede tidsstemplet — men en FRISK latch med det ægte 44-min-gap
    får os til stadig at fange reboot'et. Det var netop dette der fejlede 5. jul."""
    _reset_proc_state()
    now = datetime.now(UTC)
    store = {
        ss._LAST_ALIVE_TS: (now - timedelta(seconds=30)).isoformat(),  # klobbet → ser frisk ud
        ss._SEAM_LATCH: {"ts": (now - timedelta(seconds=40)).isoformat(),
                         "gap_s": 2640.0, "reboot": True,
                         "first_boot_ts": (now - timedelta(days=1)).isoformat()},
    }
    monkeypatch.setattr(ss, "_kv_get", lambda k, d: store.get(k, d))
    monkeypatch.setattr(ss, "_kv_set", lambda k, v: store.update({k: v}))
    seam = ss._compute_boot_seam()
    assert seam["reboot"] is True
    assert seam["gap_s"] == 2640.0  # adopteret det ægte gap, ikke de klobbede 30s


def test_boot_seam_converges_to_latch_on_next_call(monkeypatch):
    """Konvergens-fix (2. forsøg 5. jul): en proces der cachede reboot=False FØR søster-
    processen skrev latchen skal fange reboot'et på NÆSTE kald — adoption sker på HVERT kald,
    ikke kun det første. Det var netop dette der stadig fejlede i live-test #1 (api gemte
    reboot=false og overskrev runtimes reboot=true)."""
    _reset_proc_state()
    now = datetime.now(UTC)
    store = {ss._LAST_ALIVE_TS: (now - timedelta(seconds=30)).isoformat()}  # frisk puls, ingen latch
    monkeypatch.setattr(ss, "_kv_get", lambda k, d: store.get(k, d))
    monkeypatch.setattr(ss, "_kv_set", lambda k, v: store.update({k: v}))
    first = ss._compute_boot_seam()
    assert first["reboot"] is False  # første kald: latchen findes ikke endnu
    # søster-proces skriver latchen bagefter (den bootede først og så det ægte gap)
    store[ss._SEAM_LATCH] = {"ts": now.isoformat(), "gap_s": 2640.0, "reboot": True}
    second = ss._compute_boot_seam()
    assert second["reboot"] is True and second["gap_s"] == 2640.0  # konvergeret på næste kald


def test_boot_seam_ignores_stale_latch(monkeypatch):
    """Latch ældre end frisk-vinduet (>600s) ignoreres → ingen falsk 'jeg vågnede lige'
    resten af proces-livet."""
    _reset_proc_state()
    now = datetime.now(UTC)
    store = {
        ss._LAST_ALIVE_TS: (now - timedelta(seconds=30)).isoformat(),
        ss._SEAM_LATCH: {"ts": (now - timedelta(minutes=20)).isoformat(),  # 20 min > 600s
                         "gap_s": 5000.0, "reboot": True},
    }
    monkeypatch.setattr(ss, "_kv_get", lambda k, d: store.get(k, d))
    monkeypatch.setattr(ss, "_kv_set", lambda k, v: store.update({k: v}))
    seam = ss._compute_boot_seam()
    assert seam["reboot"] is False  # stale latch ignoreret; egen friske puls → intet reboot


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
