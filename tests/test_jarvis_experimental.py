"""Tests for Jarvis experimental backend extensions."""
from __future__ import annotations
import pytest


def test_settings_recall_thresholds_defaults() -> None:
    from core.runtime.settings import RuntimeSettings
    s = RuntimeSettings()
    assert s.recall_strong_threshold == 0.7
    assert s.recall_weak_threshold == 0.3
    assert s.recall_max_active == 5
    assert s.recall_repetition_multiplier == 1.5


def test_settings_cognitive_assembly_enabled_default() -> None:
    from core.runtime.settings import RuntimeSettings
    s = RuntimeSettings()
    assert s.cognitive_state_assembly_enabled is True


def test_settings_emotion_decay_factor_default() -> None:
    from core.runtime.settings import RuntimeSettings
    s = RuntimeSettings()
    assert s.emotion_decay_factor == 0.97


def test_recall_thresholds_read_from_settings() -> None:
    """Thresholds should reflect RuntimeSettings values."""
    import importlib
    import apps.api.jarvis_api.services.associative_recall as ar
    importlib.reload(ar)
    assert ar._get_strong_threshold() == 0.7
    assert ar._get_weak_threshold() == 0.3
    assert ar._get_max_active() == 5
    assert ar._get_repetition_multiplier() == 1.5


def test_recall_logs_observability() -> None:
    """recall_for_message should not crash and returns a list."""
    import importlib
    import apps.api.jarvis_api.services.associative_recall as ar
    importlib.reload(ar)
    result = ar.recall_for_message("hej verden test tekst", {})
    assert isinstance(result, list)
