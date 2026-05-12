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


def test_extract_prediction_language_matches(clean_state):
    from core.services.world_model_signal_tracking import extract_prediction_language

    text = "Det her bliver svært. Jeg tror det vil tage en uge mere."
    matches = extract_prediction_language(text)
    assert len(matches) >= 1
    phrases = [m["matched_phrase"] for m in matches]
    assert any("jeg tror" in p.lower() for p in phrases)


def test_extract_prediction_language_no_match(clean_state):
    from core.services.world_model_signal_tracking import extract_prediction_language

    matches = extract_prediction_language("Hej. Vejret er fint i dag.")
    assert matches == []


def test_extract_resolution_language_matches(clean_state):
    from core.services.world_model_signal_tracking import extract_resolution_language

    text = "Som forventet virkede løsningen ikke. Jeg tog fejl."
    matches = extract_resolution_language(text)
    phrases = [m["matched_phrase"] for m in matches]
    assert any("som forventet" in p.lower() for p in phrases)
    assert any("tog fejl" in p.lower() for p in phrases)


def test_record_prediction_nudge_persists(clean_state):
    from core.services.world_model_signal_tracking import (
        record_prediction_nudge,
        _load_nudges,
    )

    record_prediction_nudge(
        session_id="s1",
        run_id="r1",
        matched_phrase="jeg tror",
        context_excerpt="Jeg tror det virker.",
    )
    nudges = _load_nudges()
    assert len(nudges.get("prediction_nudges", [])) == 1
    n = nudges["prediction_nudges"][0]
    assert n["session_id"] == "s1"
    assert n["matched_phrase"] == "jeg tror"
    assert n["rendered_at"] == ""


def test_record_resolution_nudge_persists(clean_state):
    from core.services.world_model_signal_tracking import (
        record_resolution_nudge,
        _load_nudges,
    )

    record_resolution_nudge(
        session_id="s1",
        run_id="r1",
        matched_phrase="jeg tog fejl",
        context_excerpt="Som forventet jeg tog fejl.",
        candidate_prediction_id="",
    )
    nudges = _load_nudges()
    assert len(nudges.get("resolution_nudges", [])) == 1


def test_nudge_cap_at_20_per_kind(clean_state):
    from core.services.world_model_signal_tracking import (
        record_prediction_nudge,
        _load_nudges,
    )

    for i in range(25):
        record_prediction_nudge(
            session_id="s1",
            run_id=f"r{i}",
            matched_phrase="jeg tror",
            context_excerpt=f"context {i}",
        )
    nudges = _load_nudges()
    assert len(nudges["prediction_nudges"]) == 20
    assert nudges["prediction_nudges"][0]["run_id"] == "r5"
    assert nudges["prediction_nudges"][-1]["run_id"] == "r24"


def test_nudge_ttl_48h(clean_state):
    """Nudges get expires_at = created_at + 48h."""
    from core.services.world_model_signal_tracking import (
        record_prediction_nudge,
        _load_nudges,
    )

    record_prediction_nudge(
        session_id="s1",
        run_id="r1",
        matched_phrase="jeg tror",
        context_excerpt="x",
    )
    n = _load_nudges()["prediction_nudges"][0]
    created = datetime.fromisoformat(n["created_at"].replace("Z", "+00:00"))
    expires = datetime.fromisoformat(n["expires_at"].replace("Z", "+00:00"))
    delta = expires - created
    assert timedelta(hours=47) <= delta <= timedelta(hours=49)


def test_format_nudges_returns_empty_when_no_nudges(clean_state):
    from core.services.world_model_signal_tracking import (
        format_world_model_nudges_for_awareness,
    )
    assert format_world_model_nudges_for_awareness(session_id="s1") == ""


def test_format_nudges_renders_oldest_unrendered(clean_state):
    from core.services.world_model_signal_tracking import (
        record_prediction_nudge,
        format_world_model_nudges_for_awareness,
        _load_nudges,
    )

    record_prediction_nudge(
        session_id="s1",
        run_id="r1",
        matched_phrase="jeg tror",
        context_excerpt="Jeg tror det virker.",
    )
    out = format_world_model_nudges_for_awareness(session_id="s1")
    assert out
    assert "jeg tror" in out.lower() or "prediction" in out.lower()

    nudges = _load_nudges()
    assert nudges["prediction_nudges"][0]["rendered_at"]


def test_format_nudges_skips_already_rendered(clean_state):
    from core.services.world_model_signal_tracking import (
        record_prediction_nudge,
        format_world_model_nudges_for_awareness,
    )

    record_prediction_nudge(
        session_id="s1", run_id="r1",
        matched_phrase="jeg tror", context_excerpt="x",
    )
    first = format_world_model_nudges_for_awareness(session_id="s1")
    second = format_world_model_nudges_for_awareness(session_id="s1")
    assert first
    assert second == ""


def test_format_nudges_skips_expired(clean_state):
    from core.services.world_model_signal_tracking import (
        record_prediction_nudge,
        format_world_model_nudges_for_awareness,
        _load_nudges,
        _save_nudges,
    )

    record_prediction_nudge(
        session_id="s1", run_id="r1",
        matched_phrase="jeg tror", context_excerpt="x",
    )
    data = _load_nudges()
    data["prediction_nudges"][0]["expires_at"] = (
        datetime.now(UTC) - timedelta(hours=1)
    ).isoformat()
    _save_nudges(data)

    assert format_world_model_nudges_for_awareness(session_id="s1") == ""


def test_format_nudges_respects_killswitch(clean_state, monkeypatch):
    from core.services import world_model_signal_tracking as wm

    class FakeSettings:
        world_model_loop_enabled = False

    monkeypatch.setattr(wm, "load_settings", lambda: FakeSettings())

    wm.record_prediction_nudge(
        session_id="s1", run_id="r1",
        matched_phrase="jeg tror", context_excerpt="x",
    )
    assert wm.format_world_model_nudges_for_awareness(session_id="s1") == ""


def test_ttl_sweep_marks_expired_prediction_uncertain(clean_state):
    """Predictions with parseable horizon past grace get auto-uncertain."""
    from core.services.world_model_signal_tracking import (
        record_runtime_world_model_prediction,
        _ttl_sweep_open_predictions,
        _load_predictions,
        _save_predictions,
    )

    record_runtime_world_model_prediction(
        subject="test",
        expectation="should expire",
        horizon="i dag",
        confidence="low",
        evidence=[],
    )
    preds = _load_predictions()
    preds[0]["created_at"] = (
        datetime.now(UTC) - timedelta(hours=50)
    ).isoformat()
    _save_predictions(preds)

    result = _ttl_sweep_open_predictions(now=datetime.now(UTC))
    assert result["resolved"] >= 1

    preds_after = _load_predictions()
    assert preds_after[0]["status"] == "resolved"
    assert preds_after[0]["outcome"] == "uncertain"
    assert preds_after[0]["resolved_via"] == "ttl_auto"


def test_ttl_sweep_keeps_recent_predictions_open(clean_state):
    """Fresh predictions are not touched by TTL sweep."""
    from core.services.world_model_signal_tracking import (
        record_runtime_world_model_prediction,
        _ttl_sweep_open_predictions,
        _load_predictions,
    )

    record_runtime_world_model_prediction(
        subject="fresh",
        expectation="should stay open",
        horizon="i dag",
        confidence="low",
        evidence=[],
    )
    result = _ttl_sweep_open_predictions(now=datetime.now(UTC))
    assert result["resolved"] == 0
    preds = _load_predictions()
    assert preds[0]["status"] == "open"


def test_ttl_sweep_ignores_unparseable_horizon_initially(clean_state):
    """If horizon can't be parsed, the default grace is used (7 days)."""
    from core.services.world_model_signal_tracking import (
        record_runtime_world_model_prediction,
        _ttl_sweep_open_predictions,
        _load_predictions,
        _save_predictions,
    )

    record_runtime_world_model_prediction(
        subject="weird-horizon",
        expectation="x",
        horizon="vague time soon",
        confidence="low",
        evidence=[],
    )
    preds = _load_predictions()
    preds[0]["created_at"] = (
        datetime.now(UTC) - timedelta(days=3)
    ).isoformat()
    _save_predictions(preds)

    result = _ttl_sweep_open_predictions(now=datetime.now(UTC))
    assert result["resolved"] == 0


def test_ttl_sweep_respects_killswitch(clean_state, monkeypatch):
    from core.services import world_model_signal_tracking as wm

    class FakeSettings:
        world_model_loop_enabled = False

    monkeypatch.setattr(wm, "load_settings", lambda: FakeSettings())

    wm.record_runtime_world_model_prediction(
        subject="x", expectation="y", horizon="i dag",
        confidence="low", evidence=[],
    )
    preds = wm._load_predictions()
    preds[0]["created_at"] = (
        datetime.now(UTC) - timedelta(hours=50)
    ).isoformat()
    wm._save_predictions(preds)

    result = wm._ttl_sweep_open_predictions(now=datetime.now(UTC))
    assert result["resolved"] == 0
    assert wm._load_predictions()[0]["status"] == "open"
