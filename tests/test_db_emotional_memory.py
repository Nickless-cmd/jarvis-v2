from __future__ import annotations


def test_insert_and_get_emotional_memory_anchor(isolated_runtime) -> None:
    from core.runtime.db import (
        insert_emotional_memory_anchor,
        get_emotional_memory_anchor,
    )

    insert_emotional_memory_anchor(
        anchor_type="cognitive_episode",
        anchor_id="ce-test-1",
        captured_at="2026-05-04T12:00:00+00:00",
        mood="frustrated",
        intensity=0.62,
        confidence=0.4,
        curiosity=0.3,
        frustration=0.7,
        fatigue=0.5,
        trust=0.6,
        outcome_score=-0.4,
        outcome_source="auto",
        context_features_json='{"trigger": "visible-run:ollama/glm"}',
        source="cognitive_episodes",
    )

    row = get_emotional_memory_anchor(
        anchor_type="cognitive_episode", anchor_id="ce-test-1"
    )
    assert row is not None
    assert row["mood"] == "frustrated"
    assert abs(float(row["intensity"]) - 0.62) < 1e-6
    assert row["outcome_score"] == -0.4
    assert row["outcome_source"] == "auto"


def test_insert_is_idempotent_upsert(isolated_runtime) -> None:
    from core.runtime.db import (
        insert_emotional_memory_anchor,
        list_emotional_memory_anchors,
    )

    for intensity in (0.3, 0.7):
        insert_emotional_memory_anchor(
            anchor_type="memory_heading",
            anchor_id="some-heading",
            captured_at="2026-05-04T12:00:00+00:00",
            mood="content",
            intensity=intensity,
            context_features_json='{"heading_display": "Some Heading"}',
        )

    rows = list_emotional_memory_anchors(anchor_type="memory_heading")
    assert len(rows) == 1
    assert abs(float(rows[0]["intensity"]) - 0.7) < 1e-6


def test_list_filters_by_type_and_min_intensity(isolated_runtime) -> None:
    from core.runtime.db import (
        insert_emotional_memory_anchor,
        list_emotional_memory_anchors,
    )

    insert_emotional_memory_anchor(
        anchor_type="cognitive_episode",
        anchor_id="ce-low",
        captured_at="2026-05-04T12:00:00+00:00",
        mood="calm",
        intensity=0.2,
        context_features_json="{}",
    )
    insert_emotional_memory_anchor(
        anchor_type="cognitive_episode",
        anchor_id="ce-high",
        captured_at="2026-05-04T12:01:00+00:00",
        mood="frustrated",
        intensity=0.8,
        context_features_json="{}",
    )
    insert_emotional_memory_anchor(
        anchor_type="memory_heading",
        anchor_id="other",
        captured_at="2026-05-04T12:02:00+00:00",
        mood="content",
        intensity=0.9,
        context_features_json="{}",
    )

    rows = list_emotional_memory_anchors(
        anchor_type="cognitive_episode", min_intensity=0.5
    )
    assert len(rows) == 1
    assert rows[0]["anchor_id"] == "ce-high"


def test_update_outcome_respects_force_flag(isolated_runtime) -> None:
    from core.runtime.db import (
        insert_emotional_memory_anchor,
        update_emotional_memory_outcome,
        get_emotional_memory_anchor,
    )

    insert_emotional_memory_anchor(
        anchor_type="cognitive_episode",
        anchor_id="ce-1",
        captured_at="2026-05-04T12:00:00+00:00",
        mood="x",
        intensity=0.5,
        outcome_score=-0.4,
        outcome_source="auto",
        context_features_json="{}",
    )

    update_emotional_memory_outcome(
        anchor_type="cognitive_episode",
        anchor_id="ce-1",
        score=-0.7,
        source="override:self_review",
        force=False,
    )
    row = get_emotional_memory_anchor("cognitive_episode", "ce-1")
    assert row["outcome_score"] == -0.7  # auto can be overridden without force

    update_emotional_memory_outcome(
        anchor_type="cognitive_episode",
        anchor_id="ce-1",
        score=0.2,
        source="override:learning_policy",
        force=False,
    )
    row = get_emotional_memory_anchor("cognitive_episode", "ce-1")
    assert row["outcome_score"] == -0.7  # override-of-override blocked without force

    update_emotional_memory_outcome(
        anchor_type="cognitive_episode",
        anchor_id="ce-1",
        score=0.2,
        source="override:learning_policy",
        force=True,
    )
    row = get_emotional_memory_anchor("cognitive_episode", "ce-1")
    assert row["outcome_score"] == 0.2  # force=True wins
