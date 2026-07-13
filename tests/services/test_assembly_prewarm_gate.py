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
