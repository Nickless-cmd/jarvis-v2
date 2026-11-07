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


def test_fabricated_claim_adapter():
    """Work-claim uden tool-evidens → YELLOW; med evidens → GREEN."""
    v = ga.fabricated_claim_adapter({"text": "Fixet er live nu.", "tool_names": []})
    assert v.decision is Decision.YELLOW
    assert v.gate == "fabricated_claim"
    assert v.trigger_pattern == "fix_live"
    assert v.detected_text

    v2 = ga.fabricated_claim_adapter({"text": "Fixet er live nu.", "tool_names": ["bash"]})
    assert v2.decision is Decision.GREEN

    # tom tekst er ikke en claim
    assert ga.fabricated_claim_adapter({"text": "   "}).decision is Decision.GREEN


def _capture_events(monkeypatch) -> list[dict]:
    """Fang de events adapteren publicerer — uden tråd-race.

    Subscriber-rutningen (event → mood-bump) er allerede bevist ende-til-ende i
    tests/test_central_mood_regulator.py::test_subscriber_end_to_end_moves_mood_via_flush.
    Her måles KUN den halvdel jeg ændrede: at adapteren faktisk udsender signalet
    med det rigtige navn og den rigtige payload.
    """
    import core.services.gate_adapters as _ga
    seen: list[dict] = []

    def _fake_publish(kind, payload=None):
        seen.append({"kind": kind, **(payload or {})})
        return 0

    monkeypatch.setattr("core.eventbus.bus.event_bus.publish", _fake_publish)
    return seen


def test_diagnosis_adapter_publishes_promise_signal(monkeypatch):
    """Uverificeret completion-claim → promise.unverified → correction (mood).

    Målt 7/11-2026: central_mood_regulator mapper signalet korrekt, men den eneste
    publisher (diagnosis_gate_enforce) havde nul kaldesteder — så Jarvis' stemning
    blev aldrig jordet når han påstod at have gjort noget uden at have gjort det.
    """
    seen = _capture_events(monkeypatch)
    v = ga.diagnosis_adapter({
        "text": "Jeg har fikset det og deployet det nu.",
        "tools_used": [], "session_id": "s1", "run_id": "r1",
    })
    assert v.decision is Decision.YELLOW
    kinds = [e["kind"] for e in seen]
    assert kinds == ["promise.unverified"], f"forventede ét promise-signal, fik {kinds!r}"
    assert seen[0]["session_id"] == "s1" and seen[0]["run_id"] == "r1"
    assert seen[0]["claim"], "signalet skal bære den påstand der udløste det"


def test_diagnosis_adapter_publishes_diagnosis_signal(monkeypatch):
    """Uverificeret diagnose → diagnosis.unverified → confabulation (mood)."""
    seen = _capture_events(monkeypatch)
    v = ga.diagnosis_adapter({
        "text": "Broen er zombie — den svarer ikke på ping.",
        "tools_used": [], "session_id": "s2", "run_id": "r2",
    })
    assert v.decision is Decision.YELLOW
    kinds = [e["kind"] for e in seen]
    assert kinds == ["diagnosis.unverified"], f"forventede ét diagnose-signal, fik {kinds!r}"


def test_diagnosis_adapter_is_silent_when_evidence_exists(monkeypatch):
    """Modsat retning: med et tool i runnet er claimet verificeret → intet signal.

    Uden denne ville testen ovenfor også bestå hvis adapteren publicerede ubetinget.
    """
    seen = _capture_events(monkeypatch)
    v = ga.diagnosis_adapter({
        "text": "Jeg har fikset det og deployet det nu.",
        "tools_used": ["bash"], "session_id": "s3", "run_id": "r3",
    })
    assert v.decision is Decision.GREEN
    assert seen == [], f"verificeret claim sendte signal: {seen!r}"
