"""Tests for unified TruthGate (cluster B): aggregering + offline-paritet + register."""
from __future__ import annotations

from pathlib import Path

import core.services.gate_truth as gt
from core.services import gate_eval
from core.services.gate_kernel import Decision, GateClass, GateKernel, Verdict, worst


def _v(name, dec, action="none", reason=""):
    return Verdict(name, dec, reason, action=action)


# ── Task 1: aggregering ─────────────────────────────────────────────────
def test_truth_gate_takes_worst_decision_and_lead_reason(monkeypatch):
    monkeypatch.setattr(gt, "claim_scanner_adapter", lambda c: _v("claim_scanner", Decision.GREEN))
    monkeypatch.setattr(gt, "fact_gate_adapter",
                        lambda c: _v("fact_gate", Decision.RED, action="strip", reason="fabrikeret"))
    monkeypatch.setattr(gt, "diagnosis_adapter", lambda c: _v("diagnosis", Decision.YELLOW))
    v = gt.truth_gate({"text": "x"})
    assert v.gate == "truth" and v.decision is Decision.RED
    assert v.action == "strip" and "fabrikeret" in v.reason
    assert v.evidence == {"claim_scanner": "green", "fact_gate": "red", "diagnosis": "yellow"}


def test_truth_gate_all_green_is_green(monkeypatch):
    for name in ("claim_scanner_adapter", "fact_gate_adapter", "diagnosis_adapter"):
        monkeypatch.setattr(gt, name, lambda c, n=name: _v(n, Decision.GREEN))
    assert gt.truth_gate({"text": "alt fint"}).decision is Decision.GREEN


# ── Task 2: offline-paritet mod at køre de 3 separat ────────────────────
def test_parity_unified_equals_three_separate_on_fixtures():
    fixtures = gate_eval.load_fixtures(Path(__file__).parent / "fixtures" / "gate_eval_turns.jsonl")

    def old_three(ctx):
        vs = [gt.claim_scanner_adapter(ctx), gt.fact_gate_adapter(ctx), gt.diagnosis_adapter(ctx)]
        return {"decision": worst(vs).value}

    res = gate_eval.parity(fixtures, old_three, gt.truth_gate)
    assert res["parity"] is True, res["mismatches"]


# ── Task 3: register i Centralen ────────────────────────────────────────
def test_register_truth_nerve_registers_post_output():
    from core.services.central_core import Central
    from core.services.central_trace import TraceSink
    k = GateKernel(flag_reader=lambda key: None, emit=lambda kind, p: None)
    c = Central(k=k, sink=TraceSink())
    gt.register_truth_nerve(c)
    names = {g.name for g in k.gates_for("post_output")}
    assert "truth" in names
