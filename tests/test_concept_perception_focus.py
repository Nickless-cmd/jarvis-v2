from __future__ import annotations


def test_no_active_concepts_returns_empty_string(
    isolated_runtime, monkeypatch,
) -> None:
    from core.services import affect_modulation as am
    from core.services import emotion_concepts as ec

    monkeypatch.setattr(ec, "get_active_emotion_concepts", lambda: [])
    assert am.compute_concept_perception_focus() == ""


def test_wonder_active_returns_focus_string(isolated_runtime, monkeypatch) -> None:
    from core.services import affect_modulation as am
    from core.services import emotion_concepts as ec

    monkeypatch.setattr(
        ec, "get_active_emotion_concepts",
        lambda: [{"concept": "wonder", "intensity": 0.5}],
    )
    out = am.compute_concept_perception_focus()
    assert "mønstre" in out
    assert "anomalier" in out


def test_multiple_concepts_concatenated(isolated_runtime, monkeypatch) -> None:
    from core.services import affect_modulation as am
    from core.services import emotion_concepts as ec

    monkeypatch.setattr(
        ec, "get_active_emotion_concepts",
        lambda: [
            {"concept": "wonder", "intensity": 0.5},
            {"concept": "warmth", "intensity": 0.4},
        ],
    )
    out = am.compute_concept_perception_focus()
    assert "mønstre" in out
    assert "menneskelig tilstedeværelse" in out


def test_max_foci_capped_at_3(isolated_runtime, monkeypatch) -> None:
    from core.services import affect_modulation as am
    from core.services import emotion_concepts as ec

    monkeypatch.setattr(
        ec, "get_active_emotion_concepts",
        lambda: [
            {"concept": "wonder", "intensity": 0.8},
            {"concept": "warmth", "intensity": 0.7},
            {"concept": "playfulness", "intensity": 0.6},
            {"concept": "tenderness", "intensity": 0.5},
            {"concept": "awe", "intensity": 0.4},
        ],
    )
    out = am.compute_concept_perception_focus()
    assert "mønstre" in out
    assert "menneskelig" in out
    assert "absurde" in out
    # 4th and 5th not present
    assert "skrøbelige" not in out
    assert "skala" not in out


def test_concept_without_perception_mapping_skipped(
    isolated_runtime, monkeypatch,
) -> None:
    from core.services import affect_modulation as am
    from core.services import emotion_concepts as ec

    monkeypatch.setattr(
        ec, "get_active_emotion_concepts",
        lambda: [{"concept": "joy", "intensity": 0.7}],
    )
    assert am.compute_concept_perception_focus() == ""


def test_perception_disabled_returns_empty(isolated_runtime, monkeypatch) -> None:
    from core.runtime import settings as settings_mod
    from core.services import affect_modulation as am
    from core.services import emotion_concepts as ec

    original = settings_mod.load_settings
    def patched():
        s = original()
        s.emotion_concepts_perception_focus_enabled = False
        return s
    monkeypatch.setattr(settings_mod, "load_settings", patched)

    monkeypatch.setattr(
        ec, "get_active_emotion_concepts",
        lambda: [{"concept": "wonder", "intensity": 0.7}],
    )
    assert am.compute_concept_perception_focus() == ""
