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
