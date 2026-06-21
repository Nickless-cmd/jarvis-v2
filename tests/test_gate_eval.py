"""Tests for gate-eval/paritets-harnessen."""
from __future__ import annotations

from pathlib import Path

from core.services import gate_eval
from core.services.gate_kernel import Decision


_FIX = Path(__file__).parent / "fixtures" / "gate_eval_turns.jsonl"


def test_load_fixtures_skips_comments():
    turns = gate_eval.load_fixtures(_FIX)
    assert len(turns) == 5  # 5 data-linjer, kommentaren ignoreret
    assert all("ctx" in t for t in turns)


def test_replay_normalizes_returns():
    turns = [{"ctx": {"x": 1}}, {"ctx": {"x": 2}}]
    vs = gate_eval.replay(turns, lambda c: {"decision": "red"} if c["x"] == 2 else None)
    assert vs[0].decision is Decision.GREEN and vs[1].decision is Decision.RED


def test_replay_isolates_exceptions():
    vs = gate_eval.replay([{"ctx": {}}], lambda c: (_ for _ in ()).throw(ValueError()))
    assert vs[0].decision is Decision.SKIP and "error" in vs[0].reason


def test_parity_detects_match_and_mismatch():
    turns = [{"ctx": {"v": "a"}}, {"ctx": {"v": "b"}}]
    same = lambda c: {"decision": "green"}
    diff = lambda c: {"decision": "red"} if c["v"] == "b" else {"decision": "green"}
    assert gate_eval.parity(turns, same, same)["parity"] is True
    r = gate_eval.parity(turns, same, diff)
    assert r["parity"] is False and r["matches"] == 1 and len(r["mismatches"]) == 1


def test_score_against_ground_truth():
    turns = gate_eval.load_fixtures(_FIX)
    # Perfekt gate: returnér præcis det forventede label.
    perfect = lambda c: None  # alle "green" som default
    s = gate_eval.score(turns, perfect)
    # 3 af 5 forventer "green" → 3/5 ramt af en altid-green gate.
    assert s["labeled"] == 5 and s["hit"] == 3 and s["accuracy"] == 0.6
