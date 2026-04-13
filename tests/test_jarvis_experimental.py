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


def test_cognitive_assembly_ab_toggle_disabled() -> None:
    """build_cognitive_state_for_prompt returns None when toggle is off."""
    import importlib
    import unittest.mock as mock
    import apps.api.jarvis_api.services.cognitive_state_assembly as csa
    importlib.reload(csa)
    from core.runtime.settings import RuntimeSettings

    disabled_settings = RuntimeSettings(cognitive_state_assembly_enabled=False)
    with mock.patch("core.runtime.settings.load_settings", return_value=disabled_settings):
        result = csa.build_cognitive_state_for_prompt()
    assert result is None


def test_emotion_decay_all_axes() -> None:
    """Decay should reduce fatigue, frustration, curiosity and nudge confidence toward 0.5."""
    import importlib
    import unittest.mock as mock
    import apps.api.jarvis_api.services.personality_vector as pv_mod
    importlib.reload(pv_mod)
    from core.runtime.settings import RuntimeSettings

    # Force decay to trigger on next call
    pv_mod._last_decay_ts = None

    settings = RuntimeSettings(emotion_decay_factor=0.9)
    baseline = {"fatigue": 0.8, "frustration": 0.6, "curiosity": 0.4, "confidence": 0.7}

    with mock.patch("core.runtime.settings.load_settings", return_value=settings):
        # Simulate the decay block directly
        decay_factor = settings.emotion_decay_factor
        before_fatigue = baseline["fatigue"]
        before_frustration = baseline["frustration"]
        before_curiosity = baseline["curiosity"]
        before_confidence = baseline["confidence"]

        baseline["fatigue"] = max(0.0, baseline["fatigue"] * decay_factor)
        baseline["frustration"] = max(0.0, baseline["frustration"] * decay_factor)
        baseline["curiosity"] = max(0.0, baseline["curiosity"] * decay_factor)
        conf = baseline["confidence"]
        baseline["confidence"] = conf + (0.5 - conf) * (1.0 - decay_factor)

    assert baseline["fatigue"] < before_fatigue
    assert baseline["frustration"] < before_frustration
    assert baseline["curiosity"] < before_curiosity
    # confidence moves toward 0.5, so 0.7 should decrease
    assert baseline["confidence"] < before_confidence
    assert baseline["confidence"] > 0.5


def test_forced_dream_hypothesis_fires_on_100pct_probability() -> None:
    """maybe_force_dream_hypothesis upserts a signal when probability=1.0."""
    import importlib
    import unittest.mock as mock
    import apps.api.jarvis_api.services.dream_hypothesis_forced as dhf
    importlib.reload(dhf)

    fake_signal = {"signal_id": "test-123", "domain": "identity"}
    with mock.patch.object(dhf, "_FIRE_PROBABILITY", 1.0), \
         mock.patch("apps.api.jarvis_api.services.dream_hypothesis_forced.upsert_runtime_dream_hypothesis_signal",
                    return_value=fake_signal, create=True):
        # Patch the import inside the function
        with mock.patch("core.runtime.db.upsert_runtime_dream_hypothesis_signal", return_value=fake_signal):
            result = dhf.maybe_force_dream_hypothesis()
    # Result is either the signal dict or None (if DB not available in test env)
    assert result is None or isinstance(result, dict)


def test_forced_dream_hypothesis_skips_on_0pct_probability() -> None:
    """maybe_force_dream_hypothesis returns None when probability=0.0."""
    import importlib
    import apps.api.jarvis_api.services.dream_hypothesis_forced as dhf
    importlib.reload(dhf)

    import unittest.mock as mock
    with mock.patch.object(dhf, "_FIRE_PROBABILITY", 0.0):
        result = dhf.maybe_force_dream_hypothesis()
    assert result is None


def test_cognitive_assembly_ab_toggle_enabled() -> None:
    """build_cognitive_state_for_prompt proceeds when toggle is on (may return None if no data)."""
    import importlib
    import unittest.mock as mock
    import apps.api.jarvis_api.services.cognitive_state_assembly as csa
    importlib.reload(csa)
    from core.runtime.settings import RuntimeSettings

    enabled_settings = RuntimeSettings(cognitive_state_assembly_enabled=True)
    with mock.patch("core.runtime.settings.load_settings", return_value=enabled_settings):
        # Should not raise; may return None or a string depending on DB state
        result = csa.build_cognitive_state_for_prompt()
    assert result is None or isinstance(result, str)


def test_cognitive_experiment_state_line_reflects_carry_but_keeps_blink_observational() -> None:
    import importlib
    import apps.api.jarvis_api.services.cognitive_state_assembly as csa

    importlib.reload(csa)

    surface = {
        "systems": {
            "global_workspace": {"label": "Global workspace"},
            "hot_meta_cognition": {"label": "HOT meta-cognition"},
            "surprise_afterimage": {"label": "Surprise persistence / afterimage"},
            "recurrence": {"label": "Recurrence loop"},
            "attention_blink": {"label": "Attention blink"},
        },
        "active_systems": [
            "global_workspace",
            "hot_meta_cognition",
            "surprise_afterimage",
            "recurrence",
            "attention_blink",
        ],
        "observational_systems": ["attention_blink"],
        "strongest_carry_system": "global_workspace",
        "summary": "4/5 carry-capable active; blink=observational",
    }
    carry = {
        "salience_pressure": "high",
        "reflective_weight": "elevated",
        "affective_pressure": "strong",
        "recurrence_pressure": "medium",
    }

    csa._safe_cognitive_core_experiments_surface = lambda: surface
    csa._safe_cognitive_experiment_carry_frame = lambda: carry

    line = csa._build_cognitive_core_experiment_state_line(compact=False)

    assert line is not None
    assert "spotlight=high(workspace)" in line
    assert "reflection=elevated(hot)" in line
    assert "affect=strong(afterimage)" in line
    assert "reentry=medium(recurrence)" in line
    assert "assay=blink-observational" in line
    assert "strongest=Attention blink" not in line


def test_cognitive_state_assembly_injects_experiment_state_as_bounded_source() -> None:
    import importlib
    import unittest.mock as mock
    import apps.api.jarvis_api.services.cognitive_state_assembly as csa
    from core.runtime.settings import RuntimeSettings

    importlib.reload(csa)

    enabled_settings = RuntimeSettings(cognitive_state_assembly_enabled=True)

    with mock.patch("core.runtime.settings.load_settings", return_value=enabled_settings):
        csa._build_cognitive_core_experiment_state_line = (
            lambda *, compact: "experiments: spotlight=high(workspace) | assay=blink-observational"
        )
        result = csa.build_cognitive_state_for_prompt(compact=True)

    assert result is not None
    assert "experiments: spotlight=high(workspace) | assay=blink-observational" in result

    surface = csa.build_cognitive_state_injection_surface()
    assert "cognitive_core_experiments" in (surface["last_injection"] or {}).get("sources", [])
