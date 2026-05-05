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
