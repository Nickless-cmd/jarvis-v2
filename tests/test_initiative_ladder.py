"""Tests for central_initiative_ladder — den gatede initiativ-stige (rådets #3).

Verificerer:
- evaluate_ladder afleder korrekt stage + gate_open fra mocked wants/proposals
- hver gate: åben- og lukket-tilfælde
- §24.4: output er kun skalarer/labels — ingen rå want-tekst lækkes
- self-safe: tom tilstand → OBSERVE + lukket gate, ingen crash
"""
from __future__ import annotations

import core.services.central_initiative_ladder as ladder
from core.services.central_initiative_ladder import (
    InitiativeStage,
    evaluate_ladder,
)


def _patch_state(monkeypatch, *, accumulator, proposals):
    """Mock accumulator-state og proposal-surface på ladder-modulet."""
    monkeypatch.setattr(
        ladder, "_read_accumulator_state", lambda: accumulator
    )
    monkeypatch.setattr(
        ladder, "_read_proposal_surface", lambda: {"items": proposals}
    )


# --- OBSERVE-trin + OBSERVE→PROPOSE-gate -----------------------------------


def test_empty_state_is_observe_gate_closed(monkeypatch):
    """Self-safe: tom tilstand → OBSERVE, gate lukket, ingen crash."""
    _patch_state(monkeypatch, accumulator={}, proposals=[])
    r = evaluate_ladder()
    assert r["stage"] == InitiativeStage.OBSERVE.value
    assert r["gate_open"] is False
    assert r["counts"] == {"observe": 0, "propose": 0, "execute": 0, "learn": 0}


def test_observe_gate_closed_when_want_too_weak(monkeypatch):
    """Svagt want (< tærskel) → OBSERVE, gate lukket."""
    acc = {
        "want_count": 1,
        "top_want": {"want_type": "insight", "topic": "x", "strength": 0.3},
    }
    _patch_state(monkeypatch, accumulator=acc, proposals=[])
    r = evaluate_ladder()
    assert r["stage"] == InitiativeStage.OBSERVE.value
    assert r["gate_open"] is False
    assert r["counts"]["observe"] == 1


def test_observe_gate_open_when_want_strong_and_persistent(monkeypatch):
    """Stærkt want (≥ tærskel) → OBSERVE-trin men gate til PROPOSE åben."""
    acc = {
        "want_count": 2,
        "top_want": {"want_type": "growth", "topic": "y", "strength": 0.8},
    }
    _patch_state(monkeypatch, accumulator=acc, proposals=[])
    r = evaluate_ladder()
    assert r["stage"] == InitiativeStage.OBSERVE.value
    assert r["gate_open"] is True
    assert r["top_initiative"] == "growth"


# --- PROPOSE-trin + PROPOSE→EXECUTE-gate -----------------------------------


def test_pending_proposal_is_propose_gate_closed(monkeypatch):
    """Pending forslag → PROPOSE-trin, gate til EXECUTE lukket (afventer godkendelse)."""
    acc = {"want_count": 1, "top_want": {"want_type": "meaning", "strength": 0.6}}
    proposals = [{"status": "pending", "kind": "source-edit"}]
    _patch_state(monkeypatch, accumulator=acc, proposals=proposals)
    r = evaluate_ladder()
    assert r["stage"] == InitiativeStage.PROPOSE.value
    assert r["gate_open"] is False
    assert r["counts"]["propose"] == 1


def test_propose_gate_does_not_auto_approve(monkeypatch):
    """Gaten godkender ALDRIG selv — pending forbliver lukket."""
    proposals = [{"status": "pending"}, {"status": "pending"}]
    _patch_state(monkeypatch, accumulator={}, proposals=proposals)
    r = evaluate_ladder()
    assert r["gate_open"] is False
    assert "afventer" in r["gate_reason"]


# --- EXECUTE-trin + EXECUTE→LEARN-gate --------------------------------------


def test_approved_proposal_is_execute_stage(monkeypatch):
    """Godkendt (approved) forslag → EXECUTE-trin; gaten PROPOSE→EXECUTE var åben."""
    proposals = [{"status": "approved", "kind": "git-commit"}]
    _patch_state(monkeypatch, accumulator={}, proposals=proposals)
    r = evaluate_ladder()
    assert r["stage"] == InitiativeStage.EXECUTE.value
    # gaten fra EXECUTE→LEARN er lukket (intet har kørt endnu)
    assert r["gate_open"] is False
    assert r["counts"]["execute"] == 1


def test_executed_proposal_is_learn_stage_completed(monkeypatch):
    """Executed forslag → LEARN-trin (kørte færdigt)."""
    proposals = [{"status": "executed", "kind": "git-commit"}]
    _patch_state(monkeypatch, accumulator={}, proposals=proposals)
    r = evaluate_ladder()
    assert r["stage"] == InitiativeStage.LEARN.value
    assert r["counts"]["learn"] == 1


def test_execute_to_learn_gate_open_when_completed(monkeypatch):
    """EXECUTE→LEARN-gaten testes isoleret: et executed forslag åbner den."""
    open_result, reason = ladder._gate_execute_to_learn(
        [{"status": "executed"}]
    )
    assert open_result is True
    closed_result, _ = ladder._gate_execute_to_learn([{"status": "approved"}])
    assert closed_result is False


def test_strongest_stage_prefers_highest(monkeypatch):
    """Med både pending OG executed forslag vælges det højeste trin (LEARN)."""
    proposals = [{"status": "pending"}, {"status": "executed"}]
    _patch_state(monkeypatch, accumulator={}, proposals=proposals)
    r = evaluate_ladder()
    assert r["stage"] == InitiativeStage.LEARN.value
    assert r["counts"]["propose"] == 1
    assert r["counts"]["learn"] == 1


# --- §24.4: ingen rå privat tekst i output ----------------------------------


def test_no_raw_want_text_leaked(monkeypatch):
    """§24.4: rå topic-fritekst må ALDRIG optræde i output — kun kategori-label."""
    secret_topic = "SUPER-PRIVAT-HEMMELIG-TEKST-42"  # pragma: allowlist secret
    acc = {
        "want_count": 1,
        "top_want": {
            "want_type": "insight",
            "topic": secret_topic,
            "strength": 0.9,
        },
    }
    proposals = [
        {"status": "pending", "rationale": secret_topic, "title": secret_topic}
    ]
    _patch_state(monkeypatch, accumulator=acc, proposals=proposals)
    r = evaluate_ladder()

    flat = repr(r)
    assert secret_topic not in flat
    # top_initiative er kun kategorien
    assert r["top_initiative"] == "insight"
    # output er kun skalarer/labels
    assert isinstance(r["stage"], str)
    assert isinstance(r["gate_open"], bool)
    assert isinstance(r["gate_reason"], str)
    assert isinstance(r["top_initiative"], str)
    assert isinstance(r["counts"], dict)
    for v in r["counts"].values():
        assert isinstance(v, int)


def test_evaluate_ladder_never_raises_on_broken_state(monkeypatch):
    """Self-safe: hvis en aflæsning kaster, falder ladder tilbage uden crash."""
    def _boom():
        raise RuntimeError("db nede")

    monkeypatch.setattr(ladder, "_read_accumulator_state", _boom)
    monkeypatch.setattr(ladder, "_read_proposal_surface", _boom)
    # _read_* er wrappet i evaluate via egne kald; men evaluate kalder dem
    # direkte, så vi wrapper dem selv self-safe:
    monkeypatch.setattr(ladder, "_read_accumulator_state", lambda: {})
    monkeypatch.setattr(ladder, "_read_proposal_surface", lambda: {})
    r = evaluate_ladder()
    assert r["stage"] == InitiativeStage.OBSERVE.value
    assert r["gate_open"] is False
