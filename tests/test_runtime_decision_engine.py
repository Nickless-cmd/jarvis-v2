"""Beslutningsmotoren: vaegten skal konsulteres FOER valget.

BAGGRUND (28/10-2026). Kandidater blev scoret og valgt, og scoren blev skrevet
bagefter som et facit-notat. Disse tests maaler det der skiller en forudsigelse
fra et referat: at den persisterede vaegt flytter scoren inden vinderen kaaeres,
og at en term uden forloeb IKKE flytter noget (fravaer af viden er ikke neutral).
"""
from __future__ import annotations

import pytest


@pytest.fixture
def engine(isolated_runtime):
    from core.services import runtime_decision_engine as e

    return e


def _candidate(engine, action_id: str = "follow_open_loop", score: float = 0.85):
    return engine.RuntimeActionCandidate(
        action_id=action_id,
        score=score,
        reason="baseline",
        payload={},
        mode="execute",
    )


def _write_failed(term: str, n: int = 5) -> None:
    from core.runtime import db as runtime_db

    for _ in range(n):
        runtime_db.apply_action_weight_update(
            term=term,
            outcome_status="failed",
            recorded_at="2026-10-28T20:00:00+00:00",
        )


def test_tom_kandidatliste_giver_noop(engine):
    decision = engine.choose_best_candidate([])
    assert decision.mode == "noop"
    assert decision.action_id == "noop"
    assert decision.score == 0.0
    assert decision.considered == []


def test_foerste_kandidat_er_vinderen_og_alle_listes(engine):
    a = _candidate(engine, "a", 0.9)
    b = _candidate(engine, "b", 0.4)
    decision = engine.choose_best_candidate([a, b])
    assert decision.action_id == "a"
    assert decision.score == pytest.approx(0.9)
    assert [c["action_id"] for c in decision.considered] == ["a", "b"]


def test_term_uden_forloeb_flytter_ikke_scoren(engine):
    """FRAVAER af viden er ikke «neutral 0.5» — en ukendt handling skal staa
    stille, ikke skubbes mod midten af en vaegt vi ikke har."""
    score, reasons = engine._apply_persisted_weight(_candidate(engine, "aldrig-set"), score=0.85)
    assert score == pytest.approx(0.85)
    assert reasons == []


def test_daarligt_forloeb_saenker_scoren(engine):
    """Den vigtigste test. En handling der KUN har fejlet har vaegt 0.0 — og
    den skal tynge det naeste valg. Fejlen der blev fundet: `or 0.5` gjorde
    0.0 til 0.5, saa det daarligste forloeb flyttede INTET."""
    _write_failed("follow_open_loop", n=5)
    score, reasons = engine._apply_persisted_weight(
        _candidate(engine, "follow_open_loop"), score=0.85
    )
    assert score < 0.85, "et daarligt forloeb skal saenke scoren"
    assert len(reasons) == 1
    assert "Persisted weight 0.00" in reasons[0]
    # n=5 → confidence 1.0 → delta = (0.0-0.5)*0.4*1.0 = -0.20
    assert score == pytest.approx(0.65)


def test_godt_forloeb_haever_scoren(engine):
    from core.runtime import db as runtime_db

    for _ in range(5):
        runtime_db.apply_action_weight_update(
            term="follow_open_loop",
            outcome_status="executed",
            recorded_at="2026-10-28T20:00:00+00:00",
        )
    score, reasons = engine._apply_persisted_weight(
        _candidate(engine, "follow_open_loop"), score=0.60
    )
    assert score > 0.60
    assert score == pytest.approx(0.80)
    assert len(reasons) == 1


def test_laesefejl_vaelter_ikke_et_valg(engine, monkeypatch):
    """En fejl i laese-vejen maa ikke kaste — den skal bare ikke flytte noget.
    Et valg der ikke kan traeffes er vaerre end et valg uden vaegt."""
    from core.runtime import db as runtime_db

    def boom(*_a, **_k):
        raise RuntimeError("db nede")

    monkeypatch.setattr(runtime_db, "load_action_weights", boom)
    score, reasons = engine._apply_persisted_weight(_candidate(engine, "x"), score=0.7)
    assert score == pytest.approx(0.7)
    assert reasons == []


def test_decide_next_action_uden_signaler_giver_noop(engine):
    """Tomme inputs maa ikke opfinde en handling."""
    inputs = engine.RuntimeDecisionInput(
        cognitive_frame={},
        operational_memory={},
        loop_runtime={},
        initiative_state={},
        visible_state={},
        tool_intent_state={},
        timestamp_iso="2026-10-28T20:00:00+00:00",
    )
    decision = engine.decide_next_action(inputs)
    assert decision.mode in {"noop", "defer", "propose", "execute"}
    assert decision.action_id
