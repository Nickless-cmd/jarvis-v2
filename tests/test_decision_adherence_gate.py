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
    # Rettet 26/9-2026: det kritiske bånd lovede en automatisk revoke der ikke
    # findes i koden — og vagten låste løgnen fast. Nu pinner den i stedet at
    # eskaleringen er en HANDLING (omformulér), og at truslen er væk.
    assert "omformulér" in section
    assert "revokes decision automatisk" not in section


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


def test_handlingen_skrives_EN_gang_per_baand_ikke_per_post():
    """Målt 4/10-2026 på Bjørns levende samtale: blokken var 1.177 tokens — den
    STØRSTE i hele den dynamiske hale, 17,4 % af den — og ~297 af dem (25 %)
    var den samme sætning gentaget tolv gange.

    Handlingen er pr. BÅND, ikke pr. beslutning. Den var identisk hver gang
    fordi den aldrig kunne være andet, og den blev betalt hver tur.

    Testen tæller forekomster frem for at lede efter sætningen: en test der
    bare spurgte «står handlingen der?» ville bestå både før og efter. Det er
    præcis den fejl jeg lavede i indbakkens dublet-test samme dag.
    """
    from unittest.mock import patch

    import core.services.decision_adherence_gate as g

    kritiske = [{"decision_id": f"dec_{i:012x}", "directive": f"direktiv {i}",
                 "adherence_score": 0.0} for i in range(5)]
    imperative = [{"decision_id": f"dec_i{i:011x}", "directive": f"imp {i}",
                   "adherence_score": 0.3} for i in range(3)]
    alle = kritiske + imperative
    with patch("core.services.behavioral_decisions.list_active_decisions",
               return_value=alle), \
         patch("core.services.behavioral_decisions.count_decisions",
               return_value=len(alle)):
        t = g.decision_adherence_section()

    assert t.count("kan ikke opfyldes som formuleret") == 1, \
        "den kritiske handling gentages stadig per post"
    assert t.count("navngiv det eksplicit") == 1, \
        "den imperative handling gentages stadig per post"
    # Og den skal SIGE hvor mange den gaelder for — ellers mister linjen sin
    # adresse naar den ikke laengere staar ved sin egen post.
    assert "De 5 i kritisk band" in t
    assert "De 3 i imperativ band" in t
    # Hver beslutning har stadig sin EGEN linje med sit id. Samlingen af
    # handlingen maa ikke samle posterne.
    for d in alle:
        assert d["decision_id"] in t, f"{d['decision_id']} forsvandt"


def test_et_baand_UDEN_poster_faar_ingen_handlingslinje():
    """«+0 mere» i en anden form. En handling for et bånd der er tomt er en
    instruktion uden modtager."""
    from unittest.mock import patch

    import core.services.decision_adherence_gate as g

    kun_advisory = [{"decision_id": "dec_adv", "directive": "d",
                     "adherence_score": 0.5}]
    with patch("core.services.behavioral_decisions.list_active_decisions",
               return_value=kun_advisory), \
         patch("core.services.behavioral_decisions.count_decisions", return_value=1):
        t = g.decision_adherence_section()
    assert "kan ikke opfyldes som formuleret" not in t
    assert "navngiv det eksplicit" not in t
    assert "dec_adv" in t
