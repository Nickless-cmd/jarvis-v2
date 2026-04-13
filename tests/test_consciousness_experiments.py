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
