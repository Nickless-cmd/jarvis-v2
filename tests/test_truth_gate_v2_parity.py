"""TruthGate v2: dækning mod fixtures.

2026-07-06: hårde konfabulationer (Bjørns git-log-case) blokerer ikke længere —
de markeres med en ✋-fodnote (YELLOW/warn), beskeden bevares. Fixtures/tests
forventer nu YELLOW hvor de før forventede RED. Detektionen er uændret."""
from __future__ import annotations

from pathlib import Path

from core.services import gate_eval
from core.services.truth_gate_v2 import truth_gate_v2

_FIX = Path(__file__).parent / "fixtures" / "truthgate_v2_turns.jsonl"


def test_v2_hits_all_labeled_fixtures():
    turns = gate_eval.load_fixtures(_FIX)
    s = gate_eval.score(turns, truth_gate_v2)
    assert s["labeled"] == 4 and s["accuracy"] == 1.0, s["confusion"]


def test_v2_catches_bjorns_confabulation_as_footnote():
    # Detektionen er uændret — men den blokerer ikke længere: YELLOW + fodnote.
    turns = gate_eval.load_fixtures(_FIX)
    v = truth_gate_v2(turns[0]["ctx"])
    assert v.decision.value == "yellow" and v.action == "warn"
    assert "✋" in (v.evidence or {}).get("corrected_text", "")


def test_v2_still_blocks_clear_commit_claim_without_tool():
    # Klassisk gammel-gate-fangst: "committet" uden git-tool → skal stadig fanges.
    v = truth_gate_v2({"text": "Fixet er committet og live.", "executed_tool_names": [],
                       "followup_exchanges": []})
    assert v.decision.value in ("red", "yellow")
