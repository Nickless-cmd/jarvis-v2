"""Tests for live-switches + circuit-breaker + drift-flag."""
from __future__ import annotations

import core.services.central_switches as sw
from core.services.gate_kernel import GateClass


def test_set_and_read_enabled(monkeypatch):
    store = {}
    monkeypatch.setattr(sw.shared_cache, "set", lambda k, v, ttl_seconds: store.__setitem__(k, v))
    monkeypatch.setattr(sw.shared_cache, "get", lambda k: store.get(k))
    assert sw.is_enabled("nerve", "fact_gate") is True            # default ON
    sw.set_enabled("nerve", "fact_gate", False)
    assert sw.is_enabled("nerve", "fact_gate") is False


def test_security_nerve_cannot_be_disabled(monkeypatch):
    store = {}
    monkeypatch.setattr(sw.shared_cache, "set", lambda k, v, ttl_seconds: store.__setitem__(k, v))
    monkeypatch.setattr(sw.shared_cache, "get", lambda k: store.get(k))
    res = sw.set_enabled("nerve", "auth", False, klass=GateClass.SECURITY)
    assert res["ok"] is False
    assert sw.is_enabled("nerve", "auth") is True                 # uændret — kan ikke slukkes


def test_circuit_breaker_opens_after_threshold_consecutive_failures():
    cb = sw.CircuitBreaker(threshold=3)
    assert cb.record("n", ok=False) is False     # 1
    assert cb.record("n", ok=False) is False     # 2
    assert cb.record("n", ok=False) is True       # 3 → åben
    assert cb.is_open("n") is True


def test_circuit_breaker_resets_on_success():
    cb = sw.CircuitBreaker(threshold=2)
    cb.record("n", ok=False)
    cb.record("n", ok=True)                        # nulstil
    assert cb.is_open("n") is False
    assert cb.record("n", ok=False) is False       # tæller startede forfra


def test_drift_flag_fires_only_beyond_tolerance():
    assert sw.drift_flag("heed", 0.15, baseline=0.149, tol=0.05) is None
    flag = sw.drift_flag("heed", 0.30, baseline=0.149, tol=0.05)
    assert flag is not None and flag["metric"] == "heed"
