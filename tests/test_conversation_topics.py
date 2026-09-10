from __future__ import annotations

import pytest

from core.runtime import db_core
from core.services.conversation_topics import (
    list_conversation_topics,
    record_conversation_topic,
)


@pytest.fixture
def truth_db(monkeypatch: pytest.MonkeyPatch, tmp_path):
    db_core.close_pooled_connection()
    monkeypatch.setattr(db_core, "DB_PATH", tmp_path / "topics.db")
    yield
    db_core.close_pooled_connection()


def test_topics_merge_by_canonical_key_and_count_distinct_sessions(truth_db):
    first = record_conversation_topic(
        canonical_key="topic:deepseek-harness",
        title="DeepSeek Harness",
        summary="Inspecting the public harness",
        source_kind="visible_run",
        session_id="session-a",
        run_id="run-1",
    )
    second = record_conversation_topic(
        canonical_key="topic:deepseek-harness",
        title="DeepSeek Harness follow-up",
        summary="Checking publication evidence",
        source_kind="visible_run",
        session_id="session-b",
        run_id="run-2",
    )

    topics = list_conversation_topics(limit=10)

    assert len(topics) == 1
    assert second["topic_id"] == first["topic_id"]
    assert topics[0]["canonical_key"] == "topic:deepseek-harness"
    assert topics[0]["support_count"] == 2
    assert topics[0]["session_count"] == 2
    assert topics[0]["run_id"] == "run-2"


def test_cadence_routes_visible_run_topic_to_conversation_store(monkeypatch):
    from core.services import cadence_producers as cadence

    recorded: list[dict[str, object]] = []
    monkeypatch.setattr(
        cadence,
        "record_conversation_topic",
        lambda **values: recorded.append(values) or values,
    )
    for name in dir(cadence):
        if name.startswith("upsert_"):
            monkeypatch.setattr(cadence, name, lambda **values: values)
    for name in (
        "get_latest_cognitive_personality_vector",
        "get_latest_cognitive_user_emotional_state",
        "get_latest_cognitive_relationship_texture",
    ):
        monkeypatch.setattr(cadence, name, lambda: None)
    for name in (
        "list_cognitive_experiential_memories",
        "list_cognitive_user_emotional_states",
        "list_cognitive_habit_patterns",
        "list_cognitive_friction_signals",
        "recent_visible_runs",
    ):
        monkeypatch.setattr(cadence, name, lambda **_kwargs: [])

    counts = cadence.produce_signals_from_run(
        run_id="run-1",
        session_id="session-a",
        user_message="Inspect the published DeepSeek model harness",
        assistant_response="I will inspect it.",
        outcome_status="completed",
    )

    assert counts["world_model"] == 1
    assert len(recorded) == 1
    assert recorded[0]["canonical_key"].startswith("world-model:topic:")
    assert recorded[0]["session_id"] == "session-a"
