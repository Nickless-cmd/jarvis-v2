"""Tests for beslutnings-adherence-gaten.

Gaten oversætter aktive beslutningers adherence til eskalerende
prompt-sektioner. To fejl i den, fundet 21/9-2026, havde samme
signatur: gaten svigtede tavst i stedet for at råbe.

1. Den læste kun 20 af 44 aktive beslutninger, usorteret efter adherence —
   så de kritiske blev fortrængt af høj-prioritets-beslutninger med høj
   adherence. Af 7 kritiske nåede 2 frem.
2. `or 1.0` på adherence_score behandlede en score på præcis 0.0 som
   falsy og løftede den til 1.0. Den værste beslutning af alle blev læst
   som «doing fine» og sprunget over.

Testene her låser begge, plus loftet der aldrig må skjule en kritisk
beslutning bag advisory-støj.
"""
from __future__ import annotations

import sys
from types import ModuleType


def _fake_behavioral(monkeypatch, rows):
    """Fake-modul med begge de funktioner gaten importerer.

    Uden `count_decisions` fejler gaten med ImportError og returnerer "" —
    og en test ville så bestå ved at måle ingenting (fix 2026-09-21).
    """
    behavioral = ModuleType("core.services.behavioral_decisions")
    behavioral.count_decisions = lambda status=None: len(rows)
    behavioral.list_active_decisions = lambda limit=20: rows
    monkeypatch.setitem(sys.modules, "core.services.behavioral_decisions", behavioral)


def test_decision_adherence_gate_escalates_low_scores(monkeypatch):
    from core.services import decision_adherence_gate as gate

    _fake_behavioral(monkeypatch, [
        {"decision_id": "d1", "directive": "ship tests", "adherence_score": 0.2},
        {"decision_id": "d2", "directive": "write notes", "adherence_score": 0.5},
    ])

    section = gate.decision_adherence_section()

    assert section.startswith("\n[DECISION-ADHERENCE-GATE]")
    assert "kritisk band" in section
    assert "revokes decision automatisk" in section


def test_decision_adherence_gate_shows_zero_score(monkeypatch):
    """Regression 2026-09-21: `or 1.0` læste en score på præcis 0.0 som falsy
    og løftede den til 1.0 — den værste beslutning af alle blev sprunget over
    som «doing fine» og nåede aldrig frem."""
    from core.services import decision_adherence_gate as gate

    _fake_behavioral(monkeypatch, [
        {"decision_id": "nul", "directive": "søg modbevis", "adherence_score": 0.0},
    ])

    section = gate.decision_adherence_section()

    assert "nul:" in section
    assert "0%" in section
    assert "kritisk band" in section


def test_decision_adherence_gate_keeps_critical_past_the_cap(monkeypatch):
    """Kritiske beslutninger må ikke skubbes ud af loftet af advisory-støj —
    og resten skal tælles op, ikke forsvinde tavst."""
    from core.services import decision_adherence_gate as gate

    rows = [{"decision_id": "krit", "directive": "kritisk", "adherence_score": 0.01}]
    rows += [
        {"decision_id": f"adv{i}", "directive": "advisory", "adherence_score": 0.59}
        for i in range(30)
    ]
    _fake_behavioral(monkeypatch, rows)

    section = gate.decision_adherence_section()

    assert "krit:" in section
    assert "kritisk band" in section
    assert "flere under tærsklen" in section


def test_decision_adherence_gate_is_silent_when_all_are_healthy(monkeypatch):
    """Ingen eskalering over tærsklen → ingen sektion. Gaten må ikke støje."""
    from core.services import decision_adherence_gate as gate

    _fake_behavioral(monkeypatch, [
        {"decision_id": "fin", "directive": "gør det godt", "adherence_score": 0.95},
    ])

    assert gate.decision_adherence_section() == ""
