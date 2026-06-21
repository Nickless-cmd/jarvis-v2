"""TruthGate v2: dækning mod fixtures (inkl. Bjørns git-log-konfabulation = RED)."""
from __future__ import annotations

from pathlib import Path

from core.services import gate_eval
from core.services.truth_gate_v2 import truth_gate_v2

_FIX = Path(__file__).parent / "fixtures" / "truthgate_v2_turns.jsonl"


def test_v2_hits_all_labeled_fixtures():
    turns = gate_eval.load_fixtures(_FIX)
    s = gate_eval.score(turns, truth_gate_v2)
    assert s["labeled"] == 4 and s["accuracy"] == 1.0, s["confusion"]


def test_v2_catches_bjorns_confabulation_as_red():
    turns = gate_eval.load_fixtures(_FIX)
    v = truth_gate_v2(turns[0]["ctx"])
    assert v.decision.value == "red"


def test_v2_still_blocks_clear_commit_claim_without_tool():
    # Klassisk gammel-gate-fangst: "committet" uden git-tool → skal stadig fanges.
    v = truth_gate_v2({"text": "Fixet er committet og live.", "executed_tool_names": [],
                       "followup_exchanges": []})
    assert v.decision.value in ("red", "yellow")
