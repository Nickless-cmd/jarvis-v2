# tests/services/test_assembly_prewarm_gate.py
import sqlite3
import time
from core.services import assembly_prewarm as ap

def test_seconds_since_last_real_deepseek_call_reads_costs(monkeypatch):
    now = time.time()
    monkeypatch.setattr(ap, "_max_created_at_real_deepseek", lambda: now - 42)
    monkeypatch.setattr(ap.time, "time", lambda: now)
    assert 41 <= ap._seconds_since_last_real_deepseek_call() <= 43

def test_seconds_since_last_real_deepseek_call_none_when_no_data(monkeypatch):
    monkeypatch.setattr(ap, "_max_created_at_real_deepseek", lambda: None)
    assert ap._seconds_since_last_real_deepseek_call() is None

def test_should_prewarm_skips_when_recent_real_traffic(monkeypatch):
    monkeypatch.setattr(ap, "_seconds_since_last_real_deepseek_call", lambda: 120.0)  # <300 default
    assert ap._should_prewarm() is False

def test_should_prewarm_true_when_cold_and_no_recent_prewarm(monkeypatch):
    # Cold traffic -> traffic-gate lets it through (cross-process dedup moved to lease).
    monkeypatch.setattr(ap, "_seconds_since_last_real_deepseek_call", lambda: 9999.0)
    assert ap._should_prewarm() is True

def test_should_prewarm_true_when_no_traffic_data(monkeypatch):
    monkeypatch.setattr(ap, "_seconds_since_last_real_deepseek_call", lambda: None)
    assert ap._should_prewarm() is True

def test_min_interval_raised_to_300():
    assert ap._MIN_INTERVAL == 300.0

def test_default_interval_raised_to_600():
    assert ap._DEFAULT_INTERVAL == 600.0

def test_prewarm_once_skips_when_gate_false(monkeypatch):
    monkeypatch.setattr(ap, "_should_prewarm", lambda: False)
    # If it tried to build, it would import prompt_contract; assert it returns None without building
    assert ap.prewarm_once() is None

def test_prewarm_once_skips_when_lease_not_acquired(monkeypatch):
    monkeypatch.setattr(ap, "_should_prewarm", lambda: True)
    monkeypatch.setattr(ap, "_try_acquire_prewarm_lease", lambda interval: False)
    assert ap.prewarm_once() is None

def test_prewarm_once_builds_after_gate_and_lease(monkeypatch):
    monkeypatch.setattr(ap, "_should_prewarm", lambda: True)
    monkeypatch.setattr(ap, "_try_acquire_prewarm_lease", lambda interval: True)
    built = {"v": False}
    import sys, types
    mod = types.ModuleType("core.services.prompt_contract")
    def _build(**k):
        built["v"] = True
        return None
    mod.build_visible_chat_prompt_assembly = _build
    monkeypatch.setitem(sys.modules, "core.services.prompt_contract", mod)
    elapsed = ap.prewarm_once()
    assert built["v"] is True
    assert isinstance(elapsed, float)

def test_lease_is_single_winner(tmp_path, monkeypatch):
    db = tmp_path / "jarvis.db"
    monkeypatch.setattr(ap, "_COSTS_DB", str(db))
    # Ensure the db file/parent exists (sqlite creates the file on connect).
    first = ap._try_acquire_prewarm_lease(600)
    second = ap._try_acquire_prewarm_lease(600)
    assert first is True
    assert second is False

def test_lease_reacquire_after_interval(tmp_path, monkeypatch):
    db = tmp_path / "jarvis.db"
    monkeypatch.setattr(ap, "_COSTS_DB", str(db))
    assert ap._try_acquire_prewarm_lease(600) is True
    # A tiny interval means the row's ts is already older than now-interval.
    assert ap._try_acquire_prewarm_lease(0) is True
