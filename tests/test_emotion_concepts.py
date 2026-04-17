"""Tests for emotion concepts Lag-2 affective system."""
from __future__ import annotations

import importlib

import pytest


# ---------------------------------------------------------------------------
# DB layer tests
# ---------------------------------------------------------------------------

def test_upsert_and_list_emotion_concept_signal(isolated_runtime) -> None:
    db = isolated_runtime.db
    db.upsert_cognitive_emotion_concept_signal(
        signal_id="ec-confusion-2026-04-13",
        concept="confusion",
        intensity=0.7,
        direction="rising",
        trigger="ambiguous_input",
        source="eventbus",
        influences='["frustration", "curiosity"]',
        expires_at="2099-01-01T00:00:00+00:00",
    )
    rows = db.list_active_cognitive_emotion_concept_signals(
        now_iso="2026-04-13T10:00:00+00:00"
    )
    assert len(rows) == 1
    assert rows[0]["concept"] == "confusion"
    assert abs(rows[0]["intensity"] - 0.7) < 0.001


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fresh_ec():
    """Return a freshly reloaded emotion_concepts module with empty state."""
    import core.services.emotion_concepts as ec
    importlib.reload(ec)
    return ec


# ---------------------------------------------------------------------------
# Core service tests (in-memory — persist fails silently in background)
# ---------------------------------------------------------------------------

def test_trigger_emotion_concept_adds_to_active() -> None:
    ec = _fresh_ec()
    result = ec.trigger_emotion_concept("confusion", 0.7, trigger="test", source="test")
    assert result is not None
    assert result["concept"] == "confusion"
    assert abs(result["intensity"] - 0.7) < 0.001
    assert result["direction"] == "rising"

    active = ec.get_active_emotion_concepts()
    assert len(active) == 1
    assert active[0]["concept"] == "confusion"


def test_trigger_unknown_concept_returns_none() -> None:
    ec = _fresh_ec()
    result = ec.trigger_emotion_concept("nonexistent_concept", 0.5)
    assert result is None


def test_max_5_active_concepts_prunes_weakest() -> None:
    ec = _fresh_ec()
    concepts_with_intensities = [
        ("confusion", 0.3),
        ("insight", 0.5),
        ("doubt", 0.2),
        ("pride", 0.8),
        ("shame", 0.6),
        ("relief", 0.1),  # weakest — should be pruned when 6th added
    ]
    for concept, intensity in concepts_with_intensities:
        ec.trigger_emotion_concept(concept, intensity, trigger="test", source="test")

    active = ec.get_active_emotion_concepts()
    assert len(active) <= 5
    active_concepts = {s["concept"] for s in active}
    # "pride" (0.8) must survive
    assert "pride" in active_concepts


def test_decay_reduces_intensity() -> None:
    ec = _fresh_ec()
    ec.trigger_emotion_concept("confusion", 0.7, trigger="test", source="test")
    ec.tick_emotion_concepts(900)  # one full tick = 15 min

    active = ec.get_active_emotion_concepts()
    assert len(active) == 1
    # 0.7 * 0.85 = 0.595
    assert active[0]["intensity"] < 0.7
    assert abs(active[0]["intensity"] - 0.595) < 0.01


def test_decay_removes_concept_below_threshold() -> None:
    ec = _fresh_ec()
    ec.trigger_emotion_concept("doubt", 0.06, trigger="test", source="test")
    # After one full tick: 0.06 * 0.85 = 0.051, still above 0.05
    ec.tick_emotion_concepts(900)
    assert len(ec.get_active_emotion_concepts()) == 1
    # After second tick: 0.051 * 0.85 ≈ 0.043, below threshold
    ec.tick_emotion_concepts(900)
    assert len(ec.get_active_emotion_concepts()) == 0


def test_lag1_influence_deltas_accumulate_correctly() -> None:
    ec = _fresh_ec()
    # confusion: frustration +0.2, curiosity +0.1 at intensity 1.0
    ec.trigger_emotion_concept("confusion", 1.0, trigger="test", source="test")
    deltas = ec.get_lag1_influence_deltas()
    assert abs(deltas["frustration"] - 0.2) < 0.001
    assert abs(deltas["curiosity"] - 0.1) < 0.001
    assert abs(deltas["confidence"]) < 0.001
    assert abs(deltas["fatigue"]) < 0.001


def test_lag1_influence_clamped_at_0_5() -> None:
    ec = _fresh_ec()
    # overwhelm: fatigue +0.3, stuck: fatigue +0.2 → total 0.5 → clamped
    ec.trigger_emotion_concept("overwhelm", 1.0, trigger="test", source="test")
    ec.trigger_emotion_concept("stuck", 1.0, trigger="test", source="test")
    deltas = ec.get_lag1_influence_deltas()
    assert deltas["fatigue"] <= 0.5


def test_get_bearing_push_returns_highest_intensity_bearing_concept() -> None:
    ec = _fresh_ec()
    ec.trigger_emotion_concept("resolve", 0.4, trigger="test", source="test")
    ec.trigger_emotion_concept("caution", 0.8, trigger="test", source="test")
    push = ec.get_bearing_push()
    # caution is stronger → bearing "careful"
    assert push == "careful"


def test_get_bearing_push_returns_none_when_no_bearing_concepts() -> None:
    ec = _fresh_ec()
    ec.trigger_emotion_concept("confusion", 0.7, trigger="test", source="test")
    push = ec.get_bearing_push()
    assert push is None


# ---------------------------------------------------------------------------
# Integration: affective_meta_state
# ---------------------------------------------------------------------------

def test_live_emotional_state_includes_emotion_concepts_key() -> None:
    ec = _fresh_ec()

    import core.services.affective_meta_state as ams
    surface = ams.build_affective_meta_state_from_sources(
        embodied_state=None,
        loop_runtime=None,
        regulation_homeostasis=None,
        metabolism_state=None,
        quiet_initiative=None,
        idle_consolidation=None,
        dream_articulation=None,
        inner_voice_state=None,
        personality_vector={
            "current_bearing": "steady",
            "emotional_baseline": '{"confidence": 0.6, "fatigue": 0.1, "curiosity": 0.5, "frustration": 0.1}',
        },
        relationship_texture={},
        rhythm_state={},
    )
    assert "emotion_concepts" in surface["live_emotional_state"]


def test_live_emotional_state_applies_influence_deltas() -> None:
    ec = _fresh_ec()
    # relief: frustration -0.3 at intensity 1.0
    ec.trigger_emotion_concept("relief", 1.0, trigger="test", source="test")

    import core.services.affective_meta_state as ams
    surface = ams.build_affective_meta_state_from_sources(
        embodied_state=None,
        loop_runtime=None,
        regulation_homeostasis=None,
        metabolism_state=None,
        quiet_initiative=None,
        idle_consolidation=None,
        dream_articulation=None,
        inner_voice_state=None,
        personality_vector={
            "current_bearing": "steady",
            "emotional_baseline": '{"confidence": 0.5, "fatigue": 0.2, "curiosity": 0.3, "frustration": 0.5}',
        },
        relationship_texture={},
        rhythm_state={},
    )
    live = surface["live_emotional_state"]
    # frustration: 0.5 + (-0.3 * 1.0) = 0.2
    assert live["frustration"] is not None
    assert live["frustration"] < 0.5


def test_bearing_push_overrides_even_when_intensity_above_threshold() -> None:
    ec = _fresh_ec()
    # trust_deep → bearing "open", intensity 0.6 (above 0.4 threshold)
    ec.trigger_emotion_concept("trust_deep", 0.6, trigger="test", source="test")

    import core.services.affective_meta_state as ams
    surface = ams.build_affective_meta_state_from_sources(
        embodied_state=None,
        loop_runtime=None,
        regulation_homeostasis=None,
        metabolism_state=None,
        quiet_initiative=None,
        idle_consolidation=None,
        dream_articulation=None,
        inner_voice_state=None,
        personality_vector={"current_bearing": "steady", "emotional_baseline": "{}"},
        relationship_texture={},
        rhythm_state={},
    )
    assert surface["bearing"] == "open"


def test_bearing_push_ignored_below_threshold() -> None:
    ec = _fresh_ec()
    # trust_deep at 0.3 — below 0.4 threshold, bearing stays "even"
    ec.trigger_emotion_concept("trust_deep", 0.3, trigger="test", source="test")

    import core.services.affective_meta_state as ams
    surface = ams.build_affective_meta_state_from_sources(
        embodied_state=None,
        loop_runtime=None,
        regulation_homeostasis=None,
        metabolism_state=None,
        quiet_initiative=None,
        idle_consolidation=None,
        dream_articulation=None,
        inner_voice_state=None,
        personality_vector={"current_bearing": "steady", "emotional_baseline": "{}"},
        relationship_texture={},
        rhythm_state={},
    )
    assert surface["bearing"] == "even"


def test_bearing_push_does_not_override_stronger_affective_signal() -> None:
    ec = _fresh_ec()
    # Even with strong trust_deep, "burdened" state must win → "compressed"
    ec.trigger_emotion_concept("trust_deep", 1.0, trigger="test", source="test")

    import core.services.affective_meta_state as ams
    surface = ams.build_affective_meta_state_from_sources(
        embodied_state={"state": "strained", "strain_level": "high"},
        loop_runtime=None,
        regulation_homeostasis=None,
        metabolism_state=None,
        quiet_initiative=None,
        idle_consolidation=None,
        dream_articulation=None,
        inner_voice_state=None,
        personality_vector={"current_bearing": "steady", "emotional_baseline": "{}"},
        relationship_texture={},
        rhythm_state={},
    )
    assert surface["bearing"] == "compressed"


def test_affective_prompt_section_includes_concepts_line() -> None:
    ec = _fresh_ec()
    ec.trigger_emotion_concept("relief", 0.8, trigger="test", source="test")

    import core.services.affective_meta_state as ams
    prompt = ams.build_affective_meta_prompt_section()
    assert "concepts=" in prompt
    assert "relief" in prompt
