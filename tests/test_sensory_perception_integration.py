from __future__ import annotations


def test_engine_classifies_memory_sensory_recorded_event(isolated_runtime) -> None:
    """Engine's classify_event_change delegates memory.sensory.recorded events
    to sensory_perception_bridge.classify_sensory_change."""
    from core.runtime.db_sensory import insert_sensory_memory
    from core.services.perceptual_event_engine import classify_event_change

    for _ in range(3):
        insert_sensory_memory(
            modality="atmosphere",
            content="rolige toner og varmt lys",
            mood_tone="rolig", metadata={},
        )
    new_record = insert_sensory_memory(
        modality="atmosphere",
        content="rolige toner og varmt lys",
        mood_tone="kaotisk", metadata={},
    )

    event = {
        "id": 99,
        "kind": "memory.sensory.recorded",
        "payload": {"id": new_record["id"], "modality": "atmosphere"},
        "created_at": new_record["timestamp"],
    }
    percept = classify_event_change(event)
    assert percept is not None
    assert percept["change_type"] == "sensory-change-atmosphere"


def test_engine_returns_none_for_non_sensory_unknown_event(isolated_runtime) -> None:
    from core.services.perceptual_event_engine import classify_event_change

    event = {"id": 1, "kind": "totally.unknown.kind", "payload": {}}
    assert classify_event_change(event) is None


def test_engine_classifies_runtime_event_unchanged(isolated_runtime) -> None:
    """Existing runtime event classification still works (no regression)."""
    from core.services.perceptual_event_engine import classify_event_change

    event = {
        "id": 1,
        "kind": "runtime.visible_run_interrupted",
        "payload": {"summary": "x"},
        "created_at": "2026-05-04T12:00:00+00:00",
    }
    percept = classify_event_change(event)
    assert percept is not None
    assert percept["change_type"] == "runtime-interruption"


def test_observe_recent_changes_persists_sensory_perception(isolated_runtime) -> None:
    """End-to-end: sensory_archive.record_atmosphere → eventbus →
    observe_recent_changes → state has sensory perceptual event."""
    from core.runtime.db_sensory import insert_sensory_memory
    from core.services import sensory_archive
    from core.services.perceptual_event_engine import (
        observe_recent_changes,
        build_perception_surface,
    )

    for _ in range(3):
        insert_sensory_memory(
            modality="atmosphere",
            content="rolige toner og varmt lys i rummet",
            mood_tone="rolig", metadata={},
        )

    sensory_archive.record_atmosphere(
        "rolige toner og varmt lys i rummet",
        mood_tone="kaotisk",
    )

    result = observe_recent_changes()
    assert result["observed_count"] >= 1

    surface = build_perception_surface(scan=False)
    assert surface["active"] is True
    sensory_events = [
        e for e in surface.get("events", [])
        if str(e.get("change_type") or "").startswith("sensory-change-")
    ]
    assert len(sensory_events) >= 1
    assert sensory_events[0]["change_type"] == "sensory-change-atmosphere"


def test_sensory_perception_creates_emotional_memory_anchor(
    isolated_runtime, monkeypatch
) -> None:
    """Sensory perception flows through record_perceptual_event, which calls
    capture_emotional_anchor — verify an anchor is created."""
    from core.runtime.db import list_emotional_memory_anchors
    from core.runtime.db_sensory import insert_sensory_memory
    from core.services import emotional_memory_engine as em
    from core.services import sensory_archive
    from core.services.perceptual_event_engine import observe_recent_changes

    monkeypatch.setattr(em, "_read_current_mood", lambda: ("alert", 0.5))
    monkeypatch.setattr(em, "_read_current_dimensions", lambda: {})

    for _ in range(3):
        insert_sensory_memory(
            modality="atmosphere",
            content="rolige toner og varmt lys",
            mood_tone="rolig", metadata={},
        )
    sensory_archive.record_atmosphere(
        "rolige toner og varmt lys", mood_tone="kaotisk",
    )
    observe_recent_changes()

    anchors = list_emotional_memory_anchors(anchor_type="perceptual_event")
    assert len(anchors) >= 1


def test_disabled_bridge_passes_through_engine_without_perceptions(
    isolated_runtime, monkeypatch
) -> None:
    from core.runtime.db_sensory import insert_sensory_memory
    from core.runtime import settings as settings_mod
    from core.services import sensory_archive
    from core.services.perceptual_event_engine import (
        observe_recent_changes,
        build_perception_surface,
    )

    original_load = settings_mod.load_settings
    def patched_load():
        s = original_load()
        s.sensory_perception_bridge_enabled = False
        return s
    monkeypatch.setattr(settings_mod, "load_settings", patched_load)

    for _ in range(3):
        insert_sensory_memory(
            modality="atmosphere", content="x", mood_tone="rolig", metadata={},
        )
    sensory_archive.record_atmosphere("x", mood_tone="kaotisk")
    observe_recent_changes()

    surface = build_perception_surface(scan=False)
    sensory_events = [
        e for e in (surface.get("events") or [])
        if str(e.get("change_type") or "").startswith("sensory-change-")
    ]
    assert sensory_events == []
