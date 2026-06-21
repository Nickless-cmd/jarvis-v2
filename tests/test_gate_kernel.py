"""Tests for GateKernel — dataklasser, registry, isolation, fail-mode, flags, event."""
from __future__ import annotations

import time

from core.services.gate_kernel import (
    Decision, GateClass, Verdict, GateKernel, worst,
)


def _k(flags=None, events=None):
    flags = flags or {}
    return GateKernel(
        flag_reader=lambda key: flags.get(key),  # None = uset (kernen anvender per-nøgle-default)
        emit=lambda kind, payload: (events if events is not None else []).append((kind, payload)),
    )


# ── Task 0.1: dataklasser + præcedens ───────────────────────────────────
def test_worst_precedence():
    assert worst([]) is Decision.GREEN
    assert worst([Verdict("a", Decision.GREEN), Verdict("b", Decision.RED)]) is Decision.RED
    assert worst([Verdict("a", Decision.YELLOW), Verdict("b", Decision.SKIP)]) is Decision.YELLOW


def test_verdict_is_blocking():
    assert Verdict("a", Decision.RED).is_blocking() is True
    assert Verdict("a", Decision.GREEN).is_blocking() is False


# ── A.1: registry + run_phase ───────────────────────────────────────────
def test_run_phase_runs_registered_gates():
    k = _k()
    k.register("g1", "pre_tool", lambda ctx: {"decision": "green", "reason": "ok"})
    k.register("g2", "pre_tool", lambda ctx: Verdict("g2", Decision.YELLOW, "hmm"))
    k.register("other", "post_output", lambda ctx: None)
    vs = k.run_phase("pre_tool", {})
    assert {v.gate for v in vs} == {"g1", "g2"}
    assert worst(vs) is Decision.YELLOW


# ── A.2: isolation + fail-mode pr. klasse ───────────────────────────────
def test_cognitive_gate_exception_fails_open():
    k = _k()
    def boom(ctx): raise ValueError("x")
    k.register("c", "pre_tool", boom, klass=GateClass.COGNITIVE)
    v = k.run_phase("pre_tool", {})[0]
    assert v.decision is Decision.SKIP and "error" in v.reason


def test_security_gate_exception_fails_closed():
    k = _k()
    def boom(ctx): raise ValueError("x")
    k.register("s", "pre_tool", boom, klass=GateClass.SECURITY)
    v = k.run_phase("pre_tool", {})[0]
    assert v.decision is Decision.RED and v.action == "block"


def test_gate_timeout_isolated():
    k = _k()
    def slow(ctx): time.sleep(2.0); return None
    def fast(ctx): return {"decision": "green"}
    k.register("slow", "pre_tool", slow, timeout_ms=100)
    k.register("fast", "pre_tool", fast)
    vs = {v.gate: v for v in k.run_phase("pre_tool", {})}
    assert vs["slow"].decision is Decision.SKIP and "timeout" in vs["slow"].reason
    assert vs["fast"].decision is Decision.GREEN  # naboen upåvirket


# ── A.3: kill-switch + bypass (sikkerheds-exempt) ───────────────────────
def test_killswitch_disables_gate():
    k = _k(flags={"gate.c": False})
    k.register("c", "pre_tool", lambda ctx: {"decision": "red"})
    v = k.run_phase("pre_tool", {})[0]
    assert v.decision is Decision.SKIP and v.reason == "disabled"


def test_bypass_skips_cognitive_but_runs_security():
    k = _k(flags={"gate_kernel.bypass": True})
    k.register("cog", "pre_tool", lambda ctx: {"decision": "red"}, klass=GateClass.COGNITIVE)
    k.register("sec", "pre_tool", lambda ctx: {"decision": "green"}, klass=GateClass.SECURITY)
    vs = {v.gate: v for v in k.run_phase("pre_tool", {})}
    assert vs["cog"].decision is Decision.SKIP and vs["cog"].reason == "bypass"
    assert vs["sec"].decision is Decision.GREEN  # sikkerhed kører ALTID


# ── A.4: ét gate.evaluated-event ────────────────────────────────────────
def test_single_event_per_phase():
    events: list = []
    k = _k(events=events)
    k.register("g1", "pre_tool", lambda ctx: {"decision": "green"})
    k.register("g2", "pre_tool", lambda ctx: {"decision": "red"})
    k.run_phase("pre_tool", {})
    assert len(events) == 1
    kind, payload = events[0]
    assert kind == "gate.evaluated"
    assert payload["aggregate"] == "red" and len(payload["verdicts"]) == 2
