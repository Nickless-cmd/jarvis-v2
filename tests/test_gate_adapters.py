"""Tests for gate-adaptere (A.5) — verificér at adapterne mapper gate-resultat → Verdict."""
from __future__ import annotations

from types import SimpleNamespace

from core.services import gate_adapters as ga
from core.services.gate_kernel import Decision, GateKernel


def test_claim_scanner_adapter(monkeypatch):
    # 2026-07-06: claim_scanner appender fodnoter (bevarer teksten) → action="warn".
    import core.services.claim_scanner as cs
    monkeypatch.setattr(cs, "scan_response", lambda t: t)  # uændret → ren
    assert ga.claim_scanner_adapter({"text": "alt fint"}).decision is Decision.GREEN
    monkeypatch.setattr(cs, "scan_response", lambda t: t + "\n\n✋ fodnote")  # ændret → fanget
    v = ga.claim_scanner_adapter({"text": "påstand"})
    assert v.decision is Decision.YELLOW and v.action == "warn"


def test_fact_gate_adapter(monkeypatch):
    # 2026-07-06: fact_gate blokerer ikke længere — detekterede påstande → YELLOW/warn.
    import core.services.fact_gate as fg
    monkeypatch.setattr(fg, "fact_gate_enforce", lambda t, n=None: {"blocked": False, "block_reasons": []})
    assert ga.fact_gate_adapter({"text": "x"}).decision is Decision.GREEN
    monkeypatch.setattr(fg, "fact_gate_enforce",
                        lambda t, n=None: {"blocked": False, "block_reasons": ["fabricated"]})
    v = ga.fact_gate_adapter({"text": "x"})
    assert v.decision is Decision.YELLOW and v.action == "warn" and "fabricated" in v.reason


def test_fact_gate_adapter_block_reasons_are_dicts(monkeypatch):
    # REGRESSION (2026-06-23): fact_gate.block_reasons er DICTS, ikke strings. Et rå join
    # kastede 'expected str instance, dict found' og væltede hele truth-decide. Adapteren
    # skal udtrække en læsbar streng UDEN at kaste. (2026-07-06: nu YELLOW, ikke RED.)
    import core.services.fact_gate as fg
    monkeypatch.setattr(fg, "fact_gate_enforce", lambda t, n=None: {
        "blocked": False,
        "block_reasons": [{
            "pattern": "claimed_file_write",
            "matched": "jeg har oprettet filen",
            "description": "fil-skrivning",
            "required_tools": ["write_file"],
            "actual_tools": [],
        }],
    })
    v = ga.fact_gate_adapter({"text": "x", "tool_names": ["foo"]})
    assert v.decision is Decision.YELLOW
    assert "fil-skrivning" in v.reason  # description udtrukket, ingen TypeError


def test_diagnosis_adapter(monkeypatch):
    # 2026-07-06: diagnosis blokerer ikke længere — uverificeret completion → YELLOW/warn.
    import core.services.diagnosis_gate as dg
    monkeypatch.setattr(dg, "analyze_completion_claim",
                        lambda t, tools_used=None: SimpleNamespace(detected=True, verified=False, reason="u"))
    v = ga.diagnosis_adapter({"text": "done"})
    assert v.decision is Decision.YELLOW and v.action == "warn"
    monkeypatch.setattr(dg, "analyze_completion_claim",
                        lambda t, tools_used=None: SimpleNamespace(detected=True, verified=True, reason=""))
    assert ga.diagnosis_adapter({"text": "done"}).decision is Decision.GREEN
    monkeypatch.setattr(dg, "analyze_completion_claim",
                        lambda t, tools_used=None: SimpleNamespace(detected=False, verified=True, reason=""))
    assert ga.diagnosis_adapter({"text": "done"}).decision is Decision.GREEN


def test_register_truthgate_adapters():
    k = GateKernel(flag_reader=lambda key: None, emit=lambda kind, p: None)
    ga.register_truthgate_adapters(k)
    names = {g.name for g in k.gates_for("post_output")}
    assert {"claim_scanner", "fact_gate", "diagnosis"} <= names
    # alle i post_output, kognitiv klasse:
    for g in k.gates_for("post_output"):
        assert g.phase == "post_output"
