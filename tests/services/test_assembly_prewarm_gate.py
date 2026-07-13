# tests/services/test_assembly_prewarm_gate.py
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
    monkeypatch.setattr(ap, "_seconds_since_last_prewarm", lambda: 9999.0)
    assert ap._should_prewarm() is False

def test_should_prewarm_skips_when_another_process_just_prewarmed(monkeypatch):
    monkeypatch.setattr(ap, "_seconds_since_last_real_deepseek_call", lambda: None)  # cold
    monkeypatch.setattr(ap, "_seconds_since_last_prewarm", lambda: 10.0)  # <interval
    monkeypatch.setattr(ap, "_interval_s", lambda: 240.0)
    assert ap._should_prewarm() is False

def test_should_prewarm_true_when_cold_and_no_recent_prewarm(monkeypatch):
    monkeypatch.setattr(ap, "_seconds_since_last_real_deepseek_call", lambda: 9999.0)
    monkeypatch.setattr(ap, "_seconds_since_last_prewarm", lambda: 9999.0)
    monkeypatch.setattr(ap, "_interval_s", lambda: 240.0)
    assert ap._should_prewarm() is True
