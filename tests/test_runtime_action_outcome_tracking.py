"""Skrive-vejen: udfaldet skal FLYTTE vaegten, ikke bare logges.

BAGGRUND (28/10-2026). Foer denne aendring blev der kun INSERT'et en raekke pr.
udfald, og laese-vejen genberegnede sin snapshot fra de SAMME raa raekker. Et
daarligt forloeb forsvandt i naeste snapshot. Disse tests maaler at
`record_runtime_action_outcome` faktisk kalder vaegt-skriveren — altsaa at
koblingen findes, ikke bare at funktionerne kan kaldes hver for sig.
"""
from __future__ import annotations

import pytest


@pytest.fixture
def tracking(isolated_runtime):
    from core.services import runtime_action_outcome_tracking as t

    return t


def test_udfald_normaliseres_og_returneres(tracking):
    stored = tracking.record_runtime_action_outcome(
        action_id="follow_open_loop",
        mode="execute",
        reason="open loop found",
        score=0.85,
        payload={"loop": "x"},
        result={"status": "executed", "summary": "det gik"},
    )
    assert stored["action_id"] == "follow_open_loop"
    assert stored["decision_mode"] == "execute"
    assert stored["decision_score"] == pytest.approx(0.85)
    assert stored["result_status"] == "executed"
    assert stored["result_summary"] == "det gik"


def test_tomme_felter_faar_fornuftige_standarder(tracking):
    """En tom action_id og en manglende status maa ikke vaelte skrivningen —
    men de maa heller ikke opfinde et udfald."""
    stored = tracking.record_runtime_action_outcome(
        action_id="  ",
        mode="",
        reason="",
        score=0.0,
        payload=None,
        result={},
    )
    assert stored["action_id"] == ""
    assert stored["decision_mode"] == "noop"
    assert stored["result_status"] == "unknown"


def test_udfaldet_FLYTTTER_vaegten(tracking):
    """Det afgoerende: efter et udfald skal vaegten findes i lageret med
    n_samples=1. Skrives der kun en raekke, er der ingen laering."""
    from core.runtime import db as runtime_db

    tracking.record_runtime_action_outcome(
        action_id="bounded_self_check",
        mode="execute",
        reason="r",
        score=0.6,
        payload={},
        result={"status": "failed", "summary": "nej"},
    )
    weights = runtime_db.load_action_weights(["bounded_self_check"])
    assert "bounded_self_check" in weights
    assert weights["bounded_self_check"]["n_samples"] == 1
    # failed → target 0.0, rate 1.0 → vaegten lander paa 0.0
    assert weights["bounded_self_check"]["weight"] == pytest.approx(0.0)


def test_to_udfald_giver_to_forskellige_vaegte(tracking):
    from core.runtime import db as runtime_db

    tracking.record_runtime_action_outcome(
        action_id="a", mode="execute", reason="r", score=0.5, payload={},
        result={"status": "failed"},
    )
    tracking.record_runtime_action_outcome(
        action_id="a", mode="execute", reason="r", score=0.5, payload={},
        result={"status": "executed"},
    )
    weights = runtime_db.load_action_weights(["a"])
    assert weights["a"]["n_samples"] == 2
    assert weights["a"]["weight"] == pytest.approx(0.5)


def test_persist_action_weight_er_tavs_naar_skriveren_mangler(tracking):
    """En udgave af db-laget uden vaegt-skriveren maa ikke kaste — den skal
    bare ikke flytte noget. Ellers ville et udfald kunne vaelte en hel tur."""
    from core.runtime import db as runtime_db

    original = getattr(runtime_db, "apply_action_weight_update", None)
    try:
        if hasattr(runtime_db, "apply_action_weight_update"):
            delattr(runtime_db, "apply_action_weight_update")
        assert tracking._persist_action_weight({"action_id": "x", "result_status": "executed"}) == {}
    finally:
        if original is not None:
            runtime_db.apply_action_weight_update = original


def test_completion_outcome_label_mapper_status(tracking):
    assert tracking._completion_outcome_label("executed") == "success"
    assert tracking._completion_outcome_label("completed") == "success"
    assert tracking._completion_outcome_label("failed") == "failed"
    assert tracking._completion_outcome_label("blocked") == "failed"
    assert tracking._completion_outcome_label("skipped") == "partial"
    assert tracking._completion_outcome_label("") == "partial"


def test_consecutive_repetition_count_taeller_kun_sammenhængende(tracking):
    items = [{"action_id": "a"}, {"action_id": "a"}, {"action_id": "b"}, {"action_id": "a"}]
    # 3 x "a" i traek fra toppen? Nej: a, a, b → kun 2 i traek → 1 gentagelse.
    assert tracking._consecutive_repetition_count(items) == 1
    assert tracking._consecutive_repetition_count([]) == 0
    assert tracking._consecutive_repetition_count([{"action_id": "a"}]) == 0
    assert tracking._consecutive_repetition_count(
        [{"action_id": "a"}, {"action_id": "a"}, {"action_id": "a"}]
    ) == 2
