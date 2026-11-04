"""Tests for world-model-værktøjerne — predict_outcome + resolve_prediction.

Målt 4/11-2026: `predict_outcome` kunne ikke gøre en forudsigelse falsificerbar.
`event_kind` fandtes i læseren (`_frequency_verdict`) men blev aldrig skrevet
af producenten, så 868 åbne forudsigelser endte som `uncertain` med reason
`no-event-kind-tag-on-prediction` — og `calibration` var strukturelt `None`.
Disse tests vogter at værktøjet kan bære tag'en hele vejen ned i ledgeren.
"""
from __future__ import annotations

import pytest

from core.services import world_model_signal_tracking as wm
from core.tools import world_model_tools as wmt


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    """Isolér predictions-storen så testen ikke rører runtime-state."""
    store: list[dict] = []
    monkeypatch.setattr(wm, "_load_predictions", lambda: list(store))
    monkeypatch.setattr(wm, "_save_predictions", lambda preds: store.__setitem__(slice(None), preds))
    yield store


def test_predict_outcome_baerer_event_kind_ned_i_ledgeren(_isolate):
    """Uden dette kan sweepet aldrig afgøre om forudsigelsen holdt."""
    res = wmt._exec_predict_outcome({
        "subject": "hændelses-frekvens",
        "expectation": "frekvensen falder",
        "event_kind": "tool.completed",
    })
    assert res["status"] == "ok", res
    assert res["prediction"]["event_kind"] == "tool.completed", (
        "værktøjet smed event_kind væk — så er forudsigelsen ikke falsificerbar"
    )
    assert _isolate[0]["event_kind"] == "tool.completed"


def test_predict_outcome_uden_event_kind_er_aerlig(_isolate):
    """En forudsigelse uden tag må ikke opfinde en — den skal stå tom."""
    res = wmt._exec_predict_outcome({
        "subject": "noget",
        "expectation": "noget andet",
    })
    assert res["status"] == "ok"
    assert res["prediction"]["event_kind"] == ""


def test_predict_outcome_kraever_subject_og_expectation(_isolate):
    assert wmt._exec_predict_outcome({"expectation": "x"})["status"] == "error"
    assert wmt._exec_predict_outcome({"subject": "x"})["status"] == "error"
    assert _isolate == [], "et afvist kald må ikke skrive i ledgeren"


def test_resolve_prediction_afviser_ugyldigt_outcome(_isolate):
    res = wmt._exec_resolve_prediction({
        "prediction_id": "p1", "observed": "noget", "outcome": "måske",
    })
    assert res["status"] == "error"
