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


# ── Cluster-flip on/off (Jarvis' idé, 2026-06-22) ────────────────────────
def test_cognitive_cluster_can_be_disabled():
    from core.services import central_switches as cs
    from core.services import shared_cache
    try:
        r = cs.set_cluster_enabled("loop", False)
        assert r["ok"] is True
        assert cs.is_cluster_enabled("loop") is False
        cs.set_cluster_enabled("loop", True)
        assert cs.is_cluster_enabled("loop") is True
    finally:
        shared_cache.delete("flag:central.switch.cluster.loop")


def test_security_cluster_cannot_be_disabled():
    from core.services import central_switches as cs
    for sec in ("auth", "privacy", "execution", "mutation", "skill"):
        r = cs.set_cluster_enabled(sec, False)
        assert r["ok"] is False, sec
        # forbliver enabled trods forsøg
        assert cs.is_cluster_enabled(sec) is True


def test_is_security_cluster():
    from core.services import central_catalog as cc
    assert cc.is_security_cluster("auth") is True
    assert cc.is_security_cluster("execution") is True
    assert cc.is_security_cluster("loop") is False
    assert cc.is_security_cluster("prompt") is False


def test_decide_skips_when_cluster_disabled():
    from core.services.central_core import Central
    from core.services.central_trace import TraceSink
    from core.services.central_switches import CircuitBreaker
    from core.services import central_switches as cs
    from core.services.gate_kernel import Decision, GateClass, Verdict
    from core.services import shared_cache
    c = Central(sink=TraceSink(), breaker=CircuitBreaker(), emit=lambda *a: None)
    fn = lambda ctx: Verdict("n", Decision.RED, "would-block", klass=GateClass.COGNITIVE)
    try:
        cs.set_cluster_enabled("loop", False)
        v = c.decide("n", {"run_id": "x"}, fn, cluster="loop", klass=GateClass.COGNITIVE)
        assert v.decision is Decision.SKIP and v.reason == "cluster-disabled"
    finally:
        shared_cache.delete("flag:central.switch.cluster.loop")


def test_decide_security_ignores_cluster_disable():
    # selv hvis cluster-flag SOMEHOW sættes, må en SECURITY-nerve aldrig SKIP'e
    from core.services.central_core import Central
    from core.services.central_trace import TraceSink
    from core.services.central_switches import CircuitBreaker
    from core.services.gate_kernel import Decision, GateClass, Verdict
    from core.services import shared_cache
    c = Central(sink=TraceSink(), breaker=CircuitBreaker(), emit=lambda *a: None)
    fn = lambda ctx: Verdict("n", Decision.GREEN, "ok", klass=GateClass.SECURITY)
    try:
        shared_cache.set("flag:central.switch.cluster.auth", {"enabled": False}, ttl_seconds=99)
        v = c.decide("n", {"run_id": "x"}, fn, cluster="auth", klass=GateClass.SECURITY)
        assert v.decision is not Decision.SKIP  # security håndhæver uanset
    finally:
        shared_cache.delete("flag:central.switch.cluster.auth")
