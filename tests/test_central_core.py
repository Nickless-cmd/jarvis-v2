"""Tests for Central-facaden: observe + decide + register + singleton."""
from __future__ import annotations

import core.services.central_switches as _sw
from core.services.central_core import Central
from core.services.central_trace import TraceSink
from core.services.gate_kernel import Decision, GateClass


def _central(emitted=None):
    sink = TraceSink(maxlen=100)
    emit = (lambda kind, payload: emitted.append((kind, payload))) if emitted is not None \
        else (lambda k, p: None)
    return Central(sink=sink, emit=emit), sink


# ── observe (Task 5) ────────────────────────────────────────────────────
def test_observe_records_trace_and_emits():
    emitted = []
    c, sink = _central(emitted)
    c.observe({"run_id": "r1", "session_id": "s1", "cluster": "loop", "nerve": "budget", "rounds": 5})
    recs = sink.records_for_run("r1")
    assert len(recs) == 1 and recs[0].kind == "observe" and recs[0].nerve == "budget"
    assert recs[0].payload == {"rounds": 5}
    assert emitted and emitted[0][0] == "central.observed"


def test_observe_never_raises_on_bad_event():
    c, _ = _central()
    c.observe(None)        # må ikke kaste
    c.observe("nonsense")  # må ikke kaste


# ── decide happy + fail-mode (Task 6) ───────────────────────────────────
def test_decide_happy_path_records_verdict():
    c, sink = _central()
    v = c.decide("fact_gate", {"run_id": "r1", "session_id": "s1"},
                 lambda ctx: {"decision": "green"}, cluster="truth")
    assert v.decision is Decision.GREEN
    recs = sink.records_for_run("r1")
    assert recs and recs[-1].kind == "decide" and recs[-1].decision == "green"


def test_decide_cognitive_error_fails_open_skip():
    c, _ = _central()
    v = c.decide("budget", {"run_id": "r1"}, lambda ctx: (_ for _ in ()).throw(RuntimeError()),
                 cluster="loop", klass=GateClass.COGNITIVE)
    assert v.decision is Decision.SKIP            # fail-open


def test_decide_security_error_fails_closed_red():
    c, _ = _central()
    v = c.decide("auth", {"run_id": "r1"}, lambda ctx: (_ for _ in ()).throw(RuntimeError()),
                 cluster="auth", klass=GateClass.SECURITY)
    assert v.decision is Decision.RED and v.action == "block"   # fail-closed


# ── decide switch + breaker (Task 7) ────────────────────────────────────
def test_decide_disabled_cognitive_nerve_skips(monkeypatch):
    monkeypatch.setattr(_sw, "is_enabled", lambda scope, name: False)
    c, _ = _central()
    v = c.decide("budget", {"run_id": "r1"}, lambda ctx: {"decision": "red"}, klass=GateClass.COGNITIVE)
    assert v.decision is Decision.SKIP and v.reason == "disabled"


def test_decide_disabled_security_nerve_denies(monkeypatch):
    monkeypatch.setattr(_sw, "is_enabled", lambda scope, name: False)
    c, _ = _central()
    v = c.decide("auth", {"run_id": "r1"}, lambda ctx: {"decision": "green"}, klass=GateClass.SECURITY)
    assert v.decision is Decision.RED              # isoleret mod deny, ikke off


def test_decide_short_circuits_when_breaker_open():
    from core.services.central_switches import CircuitBreaker
    cb = CircuitBreaker(threshold=1)
    cb.record("budget", ok=False)                  # åbn kredsen
    c, _ = _central()
    c._breaker = cb
    calls = []
    c.decide("budget", {"run_id": "r1"}, lambda ctx: calls.append(1), klass=GateClass.COGNITIVE)
    assert calls == []                             # nerven blev IKKE kaldt (isoleret)


# ── register + singleton (Task 8) ───────────────────────────────────────
def test_register_passes_through_to_kernel():
    from core.services.gate_kernel import GateKernel
    k = GateKernel(flag_reader=lambda key: None, emit=lambda kind, p: None)
    c = Central(k=k, sink=TraceSink())
    c.register("budget", "loop_phase", lambda ctx: None, klass=GateClass.COGNITIVE)
    assert {g.name for g in k.gates_for("loop_phase")} == {"budget"}


def test_central_singleton_is_stable():
    from core.services.central_core import central
    assert central() is central()
