"""Rich gate-logging + mønster-læring (2026-07-13).

Gates skal være præcist attribuerbare: når en gate fyrer skal Centralen kunne se
session_id/run_id/source_file/source_line/detected_text/trigger_pattern — og
aggregere gentagne mønstre, så den kan NUDGE (vane-bryder), ikke bare blokere.
"""
from __future__ import annotations

import pytest

from core.services.gate_kernel import Decision, GateClass, Verdict


# ── Verdict: 6 nye valgfrie felter ──────────────────────────────────────────
def test_verdict_accepts_new_optional_fields_roundtrip():
    v = Verdict(
        "fact_gate", Decision.YELLOW, "reason",
        session_id="sess-1", run_id="run-1",
        source_file="/x/fact_gate.py", source_line=42,
        detected_text="2.500+ kald", trigger_pattern="self_stats",
    )
    assert v.session_id == "sess-1"
    assert v.run_id == "run-1"
    assert v.source_file == "/x/fact_gate.py"
    assert v.source_line == 42
    assert v.detected_text == "2.500+ kald"
    assert v.trigger_pattern == "self_stats"


def test_verdict_new_fields_default_empty():
    v = Verdict("g")
    assert v.session_id == ""
    assert v.run_id == ""
    assert v.source_file is None
    assert v.source_line is None
    assert v.detected_text == ""
    assert v.trigger_pattern == ""


# ── fact_gate-adapter: detected_text + trigger_pattern på Verdict ───────────
def test_fact_gate_adapter_carries_detected_and_pattern():
    from core.services.gate_adapters import fact_gate_adapter

    # "2500 kald" matcher self_stats-mønsteret uden tool-evidens → flagges.
    ctx = {"text": "Jeg har lavet 2500 kald i dag.", "tool_names": [],
           "session_id": "s-9", "run_id": "r-9"}
    v = fact_gate_adapter(ctx)
    assert v.decision is Decision.YELLOW
    assert v.trigger_pattern == "self_stats"
    assert "2500 kald" in v.detected_text
    assert v.session_id == "s-9"
    assert v.run_id == "r-9"


def test_fact_gate_adapter_green_when_no_claim():
    from core.services.gate_adapters import fact_gate_adapter

    v = fact_gate_adapter({"text": "Hej, hvordan går det?", "tool_names": []})
    assert v.decision is Decision.GREEN
    assert v.trigger_pattern == ""
    assert v.detected_text == ""


# ── truth_gate: bær lead-gatens detected/pattern videre ─────────────────────
def test_truth_gate_propagates_fact_detected_pattern():
    from core.services.gate_truth import truth_gate

    v = truth_gate({"text": "Der er 2500 kald.", "tool_names": []})
    assert v.trigger_pattern == "self_stats"
    assert "2500 kald" in v.detected_text


# ── note_suppressed_block: nye felter når de findes ─────────────────────────
def test_note_suppressed_block_emits_rich_fields(monkeypatch):
    import core.services.central_core as cc
    from core.services import gate_enforcement

    seen = {}

    class _FakeCentral:
        def observe(self, event, **kw):
            seen.update(event)

    monkeypatch.setattr(cc, "central", lambda: _FakeCentral())

    gate_enforcement.note_suppressed_block(
        "fact_gate", "truth", "ville blokeret",
        detected_text="2500 kald", trigger_pattern="self_stats",
        source_file="/x/fact_gate.py", session_id="sess-7", run_id="run-7",
    )
    assert seen.get("detected_text") == "2500 kald"
    assert seen.get("trigger_pattern") == "self_stats"
    assert seen.get("source_file") == "/x/fact_gate.py"
    assert seen.get("session_id") == "sess-7"


def test_note_suppressed_block_backward_compatible(monkeypatch):
    import core.services.central_core as cc
    from core.services import gate_enforcement

    seen = {}

    class _FakeCentral:
        def observe(self, event, **kw):
            seen.update(event)

    monkeypatch.setattr(cc, "central", lambda: _FakeCentral())
    # gammelt 3-arg-kald må stadig virke
    gate_enforcement.note_suppressed_block("veto", "veto", "grund")
    assert seen.get("nerve") == "veto"
    assert seen.get("reason") == "grund"


# ── gate.evaluated-emission: nye felter når de findes ───────────────────────
def test_gate_evaluated_includes_rich_fields():
    from core.services.gate_kernel import GateKernel

    emitted = []
    k = GateKernel(flag_reader=lambda key: None,
                   emit=lambda kind, payload: emitted.append((kind, payload)))

    def _fn(ctx):
        return Verdict("mygate", Decision.YELLOW, "flag",
                       detected_text="2500 kald", trigger_pattern="self_stats")

    k.register("mygate", "post_output", _fn)
    k.run_phase("post_output", {"session_id": "s-5", "run_id": "r-5"})

    assert emitted, "forventede et gate.evaluated event"
    payload = emitted[0][1]
    vd = payload["verdicts"][0]
    assert vd["detected_text"] == "2500 kald"
    assert vd["trigger_pattern"] == "self_stats"
    assert vd["session_id"] == "s-5"
    assert vd["run_id"] == "r-5"
    # source_file skal være fanget fra gatens registrerings-sted (denne testfil)
    assert vd["source_file"] and "test_gate_rich_logging" in vd["source_file"]


# ── Mønster-læring ──────────────────────────────────────────────────────────
def test_repeated_patterns_surfaces_after_threshold():
    from core.services import gate_pattern_learning as gpl

    gpl._reset()
    for _ in range(3):
        gpl.record_gate_pattern("self_stats", "2500 kald", session_id="s")
    rep = gpl.repeated_patterns(threshold=3)
    hits = [r for r in rep if r["pattern"] == "self_stats"]
    assert len(hits) == 1
    assert hits[0]["count"] == 3
    assert "kald" in hits[0]["sample"]


def test_repeated_patterns_below_threshold_absent():
    from core.services import gate_pattern_learning as gpl

    gpl._reset()
    gpl.record_gate_pattern("self_stats", "2500 kald")
    gpl.record_gate_pattern("self_stats", "2500 kald")
    assert gpl.repeated_patterns(threshold=3) == []


def test_different_patterns_do_not_aggregate():
    from core.services import gate_pattern_learning as gpl

    gpl._reset()
    for _ in range(3):
        gpl.record_gate_pattern("self_stats", "2500 kald")
    for _ in range(3):
        gpl.record_gate_pattern("commit_count", "45 commits")
    rep = {r["pattern"]: r["count"] for r in gpl.repeated_patterns(threshold=3)}
    assert rep.get("self_stats") == 3
    assert rep.get("commit_count") == 3
    # to distinkte nøgler — ikke slået sammen
    assert len(rep) == 2


def test_record_gate_pattern_is_self_safe_on_bad_input():
    from core.services import gate_pattern_learning as gpl

    gpl._reset()
    # må ALDRIG kaste — instrumentering må ikke vælte gate-eval
    gpl.record_gate_pattern("", "")
    gpl.record_gate_pattern(None, None)  # type: ignore[arg-type]
    assert gpl.repeated_patterns(threshold=1) == []


def test_threshold_crossing_emits_central_observe(monkeypatch):
    from core.services import gate_pattern_learning as gpl

    gpl._reset()
    observed = []
    import core.services.central_core as cc

    class _FakeCentral:
        def observe(self, event, **kw):
            observed.append(event)

    monkeypatch.setattr(cc, "central", lambda: _FakeCentral())

    for _ in range(3):
        gpl.record_gate_pattern("self_stats", "2500 kald", session_id="s")

    repeats = [e for e in observed
               if e.get("nerve") == "gate_pattern_repeat"]
    assert repeats, "forventede en central-nudge ved threshold-krydsning"
    assert repeats[0].get("cluster") == "central_meta"
