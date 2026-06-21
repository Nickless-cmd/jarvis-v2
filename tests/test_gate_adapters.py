"""Tests for gate-adaptere (A.5) — verificér at adapterne mapper gate-resultat → Verdict."""
from __future__ import annotations

from types import SimpleNamespace

from core.services import gate_adapters as ga
from core.services.gate_kernel import Decision, GateKernel


def test_claim_scanner_adapter(monkeypatch):
    import core.services.claim_scanner as cs
    monkeypatch.setattr(cs, "scan_response", lambda t: t)  # uændret → ren
    assert ga.claim_scanner_adapter({"text": "alt fint"}).decision is Decision.GREEN
    monkeypatch.setattr(cs, "scan_response", lambda t: t + " [repareret]")  # ændret → fanget
    v = ga.claim_scanner_adapter({"text": "påstand"})
    assert v.decision is Decision.YELLOW and v.action == "strip"


def test_fact_gate_adapter(monkeypatch):
    import core.services.fact_gate as fg
    monkeypatch.setattr(fg, "fact_gate_enforce", lambda t, n=None: {"blocked": False})
    assert ga.fact_gate_adapter({"text": "x"}).decision is Decision.GREEN
    monkeypatch.setattr(fg, "fact_gate_enforce",
                        lambda t, n=None: {"blocked": True, "block_reasons": ["fabricated"]})
    v = ga.fact_gate_adapter({"text": "x"})
    assert v.decision is Decision.RED and "fabricated" in v.reason


def test_diagnosis_adapter(monkeypatch):
    import core.services.diagnosis_gate as dg
    monkeypatch.setattr(dg, "analyze_completion_claim",
                        lambda t, tools_used=None: SimpleNamespace(blocked=True, reason="ingen evidens"))
    assert ga.diagnosis_adapter({"text": "done"}).decision is Decision.RED
    monkeypatch.setattr(dg, "analyze_completion_claim",
                        lambda t, tools_used=None: SimpleNamespace(blocked=False, is_claim=True, verified=False, reason="u"))
    assert ga.diagnosis_adapter({"text": "done"}).decision is Decision.YELLOW
    monkeypatch.setattr(dg, "analyze_completion_claim",
                        lambda t, tools_used=None: SimpleNamespace(blocked=False, is_claim=True, verified=True, reason=""))
    assert ga.diagnosis_adapter({"text": "done"}).decision is Decision.GREEN


def test_register_truthgate_adapters():
    k = GateKernel(flag_reader=lambda key: None, emit=lambda kind, p: None)
    ga.register_truthgate_adapters(k)
    names = {g.name for g in k.gates_for("post_output")}
    assert {"claim_scanner", "fact_gate", "diagnosis"} <= names
    # alle i post_output, kognitiv klasse:
    for g in k.gates_for("post_output"):
        assert g.phase == "post_output"
