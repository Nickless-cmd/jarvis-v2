from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest


@pytest.fixture()
def clean_state(tmp_path, monkeypatch):
    """Isolated state_store so predictions/nudges/milestones don't pollute."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("JARVIS_WORKSPACES_DIR", str(tmp_path / "workspaces"))
    import importlib
    import core.runtime.state_store as ss
    importlib.reload(ss)
    import core.services.world_model_signal_tracking as wm
    importlib.reload(wm)
    return None


def test_predict_outcome_tool_creates_prediction(clean_state):
    from core.tools.world_model_tools import _exec_predict_outcome

    result = _exec_predict_outcome({
        "subject": "deepseek-v4-flash response on cold-start",
        "expectation": "First reply will take > 8 seconds.",
        "horizon": "i dag",
        "confidence": "medium",
        "evidence": ["seen 3 cold-starts above 7s today"],
    })
    assert result["status"] == "ok"
    pred = result["prediction"]
    assert pred["status"] == "open"
    assert pred["subject"].startswith("deepseek-v4-flash")
    assert pred["confidence"] == "medium"


def test_predict_outcome_validates_required_fields(clean_state):
    from core.tools.world_model_tools import _exec_predict_outcome

    result = _exec_predict_outcome({
        "subject": "",
        "expectation": "x",
    })
    assert result["status"] == "error"

    result = _exec_predict_outcome({
        "subject": "x",
        "expectation": "",
    })
    assert result["status"] == "error"


def test_predict_outcome_respects_killswitch(clean_state, monkeypatch):
    from core.tools import world_model_tools as wmt

    class FakeSettings:
        world_model_loop_enabled = False

    monkeypatch.setattr(wmt, "load_settings", lambda: FakeSettings())

    # Spec choice: tool keeps working as a ledger even when loop is off.
    result = wmt._exec_predict_outcome({
        "subject": "ledger-test",
        "expectation": "still works",
    })
    assert result["status"] == "ok"


def test_resolve_prediction_tool_supports_open_prediction(clean_state):
    from core.tools.world_model_tools import (
        _exec_predict_outcome,
        _exec_resolve_prediction,
    )

    r1 = _exec_predict_outcome({
        "subject": "test",
        "expectation": "x",
    })
    pid = r1["prediction"]["prediction_id"]

    r2 = _exec_resolve_prediction({
        "prediction_id": pid,
        "observed": "x happened",
        "outcome": "supported",
    })
    assert r2["status"] == "ok"

    from core.services.world_model_signal_tracking import _load_predictions
    items = _load_predictions()
    matching = [p for p in items if p.get("prediction_id") == pid]
    assert len(matching) == 1
    assert matching[0]["status"] == "resolved"
    assert matching[0]["outcome"] == "supported"
    assert matching[0]["resolved_via"] == "tool"


def test_resolve_prediction_tool_validates_outcome(clean_state):
    from core.tools.world_model_tools import (
        _exec_predict_outcome,
        _exec_resolve_prediction,
    )

    r1 = _exec_predict_outcome({"subject": "x", "expectation": "y"})
    pid = r1["prediction"]["prediction_id"]

    result = _exec_resolve_prediction({
        "prediction_id": pid,
        "observed": "z",
        "outcome": "invalid-outcome",
    })
    assert result["status"] == "error"


def test_tool_definitions_registered():
    from core.tools.world_model_tools import (
        WORLD_MODEL_TOOL_DEFINITIONS,
        WORLD_MODEL_TOOL_HANDLERS,
    )

    names = [
        (e.get("function") or {}).get("name")
        for e in WORLD_MODEL_TOOL_DEFINITIONS
        if isinstance(e, dict)
    ]
    assert "predict_outcome" in names
    assert "resolve_prediction" in names
    assert "predict_outcome" in WORLD_MODEL_TOOL_HANDLERS
    assert "resolve_prediction" in WORLD_MODEL_TOOL_HANDLERS


def test_tools_registered_in_simple_tools():
    """End-to-end: the splat into simple_tools picks up our new tools."""
    from core.tools.simple_tools import TOOL_DEFINITIONS, _TOOL_HANDLERS

    names = [
        (e.get("function") or {}).get("name")
        for e in TOOL_DEFINITIONS
        if isinstance(e, dict)
    ]
    assert "predict_outcome" in names
    assert "resolve_prediction" in names
    assert "predict_outcome" in _TOOL_HANDLERS
    assert "resolve_prediction" in _TOOL_HANDLERS
