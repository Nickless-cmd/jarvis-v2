"""Tests for consciousness experiment subsystems."""
from __future__ import annotations
import pytest


# ---------------------------------------------------------------------------
# Shared infrastructure: experiment toggle
# ---------------------------------------------------------------------------

def test_experiment_enabled_default_true(isolated_runtime) -> None:
    db = isolated_runtime.db
    # Default: no row → enabled
    assert db.get_experiment_enabled("recurrence_loop") is True


def test_experiment_toggle(isolated_runtime) -> None:
    db = isolated_runtime.db
    db.set_experiment_enabled("recurrence_loop", False)
    assert db.get_experiment_enabled("recurrence_loop") is False
    db.set_experiment_enabled("recurrence_loop", True)
    assert db.get_experiment_enabled("recurrence_loop") is True


def test_experiment_toggle_independent(isolated_runtime) -> None:
    db = isolated_runtime.db
    db.set_experiment_enabled("meta_cognition", False)
    assert db.get_experiment_enabled("recurrence_loop") is True
    assert db.get_experiment_enabled("meta_cognition") is False


# ---------------------------------------------------------------------------
# Experiment 1: Recurrence Loop
# ---------------------------------------------------------------------------

def test_recurrence_db_insert_and_fetch(isolated_runtime) -> None:
    db = isolated_runtime.db
    db.insert_recurrence_iteration(
        iteration_id="rec-test-001",
        content="Jeg tænker på kompleksitet og usikkerhed",
        keywords='["kompleksitet", "usikkerhed", "tænker"]',
        stability_score=0.72,
        iteration_number=3,
    )
    result = db.get_latest_recurrence_iteration()
    assert result is not None
    assert result["iteration_id"] == "rec-test-001"
    assert abs(result["stability_score"] - 0.72) < 0.001
    assert result["iteration_number"] == 3


def test_jaccard_similarity_identical() -> None:
    import importlib
    import apps.api.jarvis_api.services.recurrence_loop_daemon as rld
    importlib.reload(rld)
    score = rld._jaccard_similarity({"a", "b", "c"}, {"a", "b", "c"})
    assert abs(score - 1.0) < 0.001


def test_jaccard_similarity_disjoint() -> None:
    import importlib
    import apps.api.jarvis_api.services.recurrence_loop_daemon as rld
    importlib.reload(rld)
    score = rld._jaccard_similarity({"a", "b"}, {"c", "d"})
    assert abs(score - 0.0) < 0.001


def test_jaccard_similarity_partial() -> None:
    import importlib
    import apps.api.jarvis_api.services.recurrence_loop_daemon as rld
    importlib.reload(rld)
    score = rld._jaccard_similarity({"a", "b", "c"}, {"b", "c", "d"})
    # intersection=2, union=4 → 0.5
    assert abs(score - 0.5) < 0.001


def test_extract_keywords_filters_short() -> None:
    import importlib
    import apps.api.jarvis_api.services.recurrence_loop_daemon as rld
    importlib.reload(rld)
    kws = rld._extract_keywords("jeg er glad men også bekymret")
    assert "er" not in kws
    assert "jeg" not in kws
    assert "bekymret" in kws or "glad" in kws


def test_tick_recurrence_skips_when_disabled(isolated_runtime) -> None:
    isolated_runtime.db.set_experiment_enabled("recurrence_loop", False)
    import importlib
    import apps.api.jarvis_api.services.recurrence_loop_daemon as rld
    importlib.reload(rld)
    result = rld.tick_recurrence_loop_daemon()
    assert result["generated"] is False
    assert result["reason"] == "disabled"


def test_trigger_emotion_concept_custom_lifetime() -> None:
    import importlib
    import apps.api.jarvis_api.services.emotion_concepts as ec
    importlib.reload(ec)
    result = ec.trigger_emotion_concept("anticipation", 0.7, lifetime_hours=4.0)
    assert result is not None
    # expires_at should be ~4h from now, not 2h
    from datetime import UTC, datetime, timedelta
    expires = datetime.fromisoformat(result["expires_at"])
    now = datetime.now(UTC)
    delta_hours = (expires - now).total_seconds() / 3600
    assert 3.5 < delta_hours < 4.5
