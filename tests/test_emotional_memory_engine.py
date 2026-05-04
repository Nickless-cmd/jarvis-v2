from __future__ import annotations


def test_outcome_auto_deriv_completed_no_error_is_positive(isolated_runtime) -> None:
    from core.services.emotional_memory_engine import _derive_outcome_score

    score, source = _derive_outcome_score(
        status="completed", error="", tool_error_count=0
    )
    assert score is not None
    assert 0.5 < score < 0.7
    assert source == "auto"


def test_outcome_auto_deriv_completed_with_errors_is_neutral(isolated_runtime) -> None:
    from core.services.emotional_memory_engine import _derive_outcome_score

    score, source = _derive_outcome_score(
        status="completed", error="some error", tool_error_count=1
    )
    assert score == 0.0
    assert source == "auto"


def test_outcome_auto_deriv_interrupted_is_negative(isolated_runtime) -> None:
    from core.services.emotional_memory_engine import _derive_outcome_score

    score, source = _derive_outcome_score(
        status="interrupted", error="", tool_error_count=0
    )
    assert score is not None
    assert -0.5 < score < -0.3
    assert source == "auto"


def test_outcome_auto_deriv_timeout_error_is_strongly_negative(isolated_runtime) -> None:
    from core.services.emotional_memory_engine import _derive_outcome_score

    score, source = _derive_outcome_score(
        status="error", error="upstream timeout while reading", tool_error_count=0
    )
    assert score is not None
    assert -0.8 < score < -0.6
    assert source == "auto"


def test_outcome_auto_deriv_bad_request_is_strongly_negative(isolated_runtime) -> None:
    from core.services.emotional_memory_engine import _derive_outcome_score

    score, source = _derive_outcome_score(
        status="error", error="HTTP 400 bad request", tool_error_count=0
    )
    assert score is not None
    assert -0.8 < score < -0.6
    assert source == "auto"


def test_outcome_auto_deriv_unknown_status_returns_none(isolated_runtime) -> None:
    from core.services.emotional_memory_engine import _derive_outcome_score

    score, source = _derive_outcome_score(
        status="something_weird", error="", tool_error_count=0
    )
    assert score is None
    assert source is None


def test_classify_error_categories(isolated_runtime) -> None:
    from core.services.emotional_memory_engine import _classify_error

    assert _classify_error("upstream timeout") == "timeout"
    assert _classify_error("HTTP 400 Bad Request") == "bad_request"
    assert _classify_error("tool xyz failed: read error") == "tool_error"
    assert _classify_error("") == "none"
    assert _classify_error("unknown gibberish") == "other"


def test_count_tool_errors_heuristic(isolated_runtime) -> None:
    from core.services.emotional_memory_engine import _count_tool_errors

    assert _count_tool_errors("", []) == 0
    assert _count_tool_errors("tool x failed", ["x"]) == 1
    assert _count_tool_errors(
        "tool a failed; tool b error: 500", ["a", "b", "c"]
    ) == 2


def test_capture_persists_full_affect_vector(isolated_runtime, monkeypatch) -> None:
    from core.runtime.db import get_emotional_memory_anchor
    from core.services import emotional_memory_engine as em

    monkeypatch.setattr(em, "_read_current_mood", lambda: ("frustrated", 0.62))
    monkeypatch.setattr(
        em,
        "_read_current_dimensions",
        lambda: {
            "confidence": 0.4,
            "curiosity": 0.3,
            "frustration": 0.7,
            "fatigue": 0.5,
            "trust": 0.6,
        },
    )

    result = em.capture_emotional_anchor(
        anchor_type="cognitive_episode",
        anchor_id="ce-x1",
        context_features={"trigger": "visible-run:ollama/glm", "tool_names": ["a"]},
        auto_outcome_inputs={
            "outcome_status": "interrupted",
            "error": "",
            "tool_error_count": 0,
        },
        source="cognitive_episodes",
    )
    assert result is not None
    assert result["mood"] == "frustrated"

    row = get_emotional_memory_anchor("cognitive_episode", "ce-x1")
    assert row is not None
    assert row["frustration"] == 0.7
    assert row["fatigue"] == 0.5
    assert row["outcome_score"] == -0.4
    assert row["outcome_source"] == "auto"


def test_capture_with_unavailable_dimensions_still_persists_mood(
    isolated_runtime, monkeypatch
) -> None:
    from core.runtime.db import get_emotional_memory_anchor
    from core.services import emotional_memory_engine as em

    monkeypatch.setattr(em, "_read_current_mood", lambda: ("calm", 0.4))

    def _raise():
        raise RuntimeError("affect surface broken")

    monkeypatch.setattr(em, "_read_current_dimensions", _raise)

    em.capture_emotional_anchor(
        anchor_type="memory_heading",
        anchor_id="some-heading",
        context_features={"heading_display": "Some Heading"},
    )
    row = get_emotional_memory_anchor("memory_heading", "some-heading")
    assert row is not None
    assert row["mood"] == "calm"
    assert row["confidence"] is None
    assert row["frustration"] is None


def test_capture_returns_none_when_mood_unavailable(
    isolated_runtime, monkeypatch
) -> None:
    from core.services import emotional_memory_engine as em

    def _raise():
        raise RuntimeError("oscillator down")

    monkeypatch.setattr(em, "_read_current_mood", _raise)

    result = em.capture_emotional_anchor(
        anchor_type="cognitive_episode",
        anchor_id="ce-broken",
        context_features={},
    )
    assert result is None


def test_capture_idempotent_overwrites_existing(
    isolated_runtime, monkeypatch
) -> None:
    from core.runtime.db import (
        get_emotional_memory_anchor,
        list_emotional_memory_anchors,
    )
    from core.services import emotional_memory_engine as em

    monkeypatch.setattr(em, "_read_current_dimensions", lambda: {})

    monkeypatch.setattr(em, "_read_current_mood", lambda: ("calm", 0.3))
    em.capture_emotional_anchor(
        anchor_type="cognitive_episode",
        anchor_id="ce-dup",
        context_features={},
    )

    monkeypatch.setattr(em, "_read_current_mood", lambda: ("frustrated", 0.7))
    em.capture_emotional_anchor(
        anchor_type="cognitive_episode",
        anchor_id="ce-dup",
        context_features={},
    )

    rows = list_emotional_memory_anchors(anchor_type="cognitive_episode")
    assert len(rows) == 1
    row = get_emotional_memory_anchor("cognitive_episode", "ce-dup")
    assert row["mood"] == "frustrated"


def test_prune_keeps_recent_anchors(isolated_runtime) -> None:
    from datetime import UTC, datetime, timedelta
    from core.runtime.db import (
        insert_emotional_memory_anchor,
        list_emotional_memory_anchors,
    )
    from core.services.emotional_memory_engine import prune_aged_anchors

    now = datetime.now(UTC)
    insert_emotional_memory_anchor(
        anchor_type="cognitive_episode",
        anchor_id="recent",
        captured_at=(now - timedelta(days=5)).isoformat(),
        mood="x",
        intensity=0.2,
        context_features_json="{}",
    )
    removed = prune_aged_anchors()
    assert removed == 0
    assert len(list_emotional_memory_anchors()) == 1


def test_prune_removes_old_low_signal_anchors(isolated_runtime) -> None:
    from datetime import UTC, datetime, timedelta
    from core.runtime.db import (
        insert_emotional_memory_anchor,
        list_emotional_memory_anchors,
    )
    from core.services.emotional_memory_engine import prune_aged_anchors

    now = datetime.now(UTC)
    insert_emotional_memory_anchor(
        anchor_type="cognitive_episode",
        anchor_id="old-bland",
        captured_at=(now - timedelta(days=200)).isoformat(),
        mood="x",
        intensity=0.2,
        outcome_score=0.0,
        context_features_json="{}",
    )
    removed = prune_aged_anchors()
    assert removed == 1
    assert list_emotional_memory_anchors() == []


def test_prune_keeps_old_intense_anchors(isolated_runtime) -> None:
    from datetime import UTC, datetime, timedelta
    from core.runtime.db import (
        insert_emotional_memory_anchor,
        list_emotional_memory_anchors,
    )
    from core.services.emotional_memory_engine import prune_aged_anchors

    now = datetime.now(UTC)
    insert_emotional_memory_anchor(
        anchor_type="cognitive_episode",
        anchor_id="old-intense",
        captured_at=(now - timedelta(days=200)).isoformat(),
        mood="x",
        intensity=0.85,
        outcome_score=0.0,
        context_features_json="{}",
    )
    removed = prune_aged_anchors()
    assert removed == 0
    assert len(list_emotional_memory_anchors()) == 1


def test_prune_keeps_old_anchors_with_strongly_negative_outcome(
    isolated_runtime,
) -> None:
    from datetime import UTC, datetime, timedelta
    from core.runtime.db import (
        insert_emotional_memory_anchor,
        list_emotional_memory_anchors,
    )
    from core.services.emotional_memory_engine import prune_aged_anchors

    now = datetime.now(UTC)
    insert_emotional_memory_anchor(
        anchor_type="cognitive_episode",
        anchor_id="old-bad",
        captured_at=(now - timedelta(days=200)).isoformat(),
        mood="x",
        intensity=0.3,
        outcome_score=-0.7,
        context_features_json="{}",
    )
    removed = prune_aged_anchors()
    assert removed == 0
    assert len(list_emotional_memory_anchors()) == 1


def test_find_similar_tier1_structured_match_episode(isolated_runtime) -> None:
    import json
    from core.runtime.db import insert_emotional_memory_anchor
    from core.services.emotional_memory_engine import find_similar_anchors

    insert_emotional_memory_anchor(
        anchor_type="cognitive_episode",
        anchor_id="ce-1",
        captured_at="2026-05-04T12:00:00+00:00",
        mood="frustrated",
        intensity=0.6,
        context_features_json=json.dumps({
            "trigger": "visible-run:ollama/glm",
            "tool_names": ["read_file", "propose_source_edit"],
            "outcome_status": "interrupted",
            "error_kind": "timeout",
            "summary": "...",
        }),
    )
    insert_emotional_memory_anchor(
        anchor_type="cognitive_episode",
        anchor_id="ce-2",
        captured_at="2026-05-04T12:01:00+00:00",
        mood="frustrated",
        intensity=0.7,
        context_features_json=json.dumps({
            "trigger": "visible-run:ollama/glm",
            "tool_names": ["read_file"],
            "outcome_status": "interrupted",
            "error_kind": "timeout",
            "summary": "...",
        }),
    )
    insert_emotional_memory_anchor(
        anchor_type="cognitive_episode",
        anchor_id="ce-other",
        captured_at="2026-05-04T12:02:00+00:00",
        mood="calm",
        intensity=0.3,
        context_features_json=json.dumps({
            "trigger": "voice-input",
            "tool_names": ["speak"],
            "outcome_status": "completed",
            "error_kind": "none",
            "summary": "...",
        }),
    )

    matches = find_similar_anchors(
        anchor_type="cognitive_episode",
        context_features={
            "trigger": "visible-run:ollama/glm",
            "tool_names": ["read_file", "propose_source_edit"],
            "outcome_status": "interrupted",
            "error_kind": "timeout",
            "summary": "fresh run",
        },
    )
    ids = [m["anchor_id"] for m in matches]
    assert "ce-1" in ids and "ce-2" in ids
    assert "ce-other" not in ids


def test_find_similar_tier2_lexical_fallback_when_tier1_thin(
    isolated_runtime,
) -> None:
    import json
    from core.runtime.db import insert_emotional_memory_anchor
    from core.services.emotional_memory_engine import find_similar_anchors

    insert_emotional_memory_anchor(
        anchor_type="cognitive_episode",
        anchor_id="lex-1",
        captured_at="2026-05-04T12:00:00+00:00",
        mood="frustrated",
        intensity=0.6,
        context_features_json=json.dumps({
            "trigger": "trigger-a",
            "tool_names": ["x"],
            "outcome_status": "completed",
            "error_kind": "none",
            "summary": "propose source edit attempt failed during commit hook",
        }),
    )
    insert_emotional_memory_anchor(
        anchor_type="cognitive_episode",
        anchor_id="lex-2",
        captured_at="2026-05-04T12:01:00+00:00",
        mood="frustrated",
        intensity=0.6,
        context_features_json=json.dumps({
            "trigger": "trigger-b",
            "tool_names": ["y"],
            "outcome_status": "completed",
            "error_kind": "none",
            "summary": "propose source edit attempt failed during commit hook again",
        }),
    )

    matches = find_similar_anchors(
        anchor_type="cognitive_episode",
        context_features={
            "trigger": "totally-different-trigger",
            "tool_names": ["unrelated"],
            "outcome_status": "completed",
            "error_kind": "none",
            "summary": "propose source edit attempt failed during commit hook",
        },
    )
    ids = [m["anchor_id"] for m in matches]
    assert "lex-1" in ids and "lex-2" in ids


def test_find_similar_aging_weights_old_anchors_lower(isolated_runtime) -> None:
    import json
    from datetime import UTC, datetime, timedelta
    from core.runtime.db import insert_emotional_memory_anchor
    from core.services.emotional_memory_engine import find_similar_anchors

    now = datetime.now(UTC)
    feats = json.dumps({
        "trigger": "x",
        "tool_names": ["a"],
        "outcome_status": "completed",
        "error_kind": "none",
        "summary": "exactly the same",
    })
    insert_emotional_memory_anchor(
        anchor_type="cognitive_episode",
        anchor_id="fresh",
        captured_at=now.isoformat(),
        mood="x", intensity=0.5,
        context_features_json=feats,
    )
    insert_emotional_memory_anchor(
        anchor_type="cognitive_episode",
        anchor_id="aged",
        captured_at=(now - timedelta(days=60)).isoformat(),
        mood="x", intensity=0.5,
        context_features_json=feats,
    )

    matches = find_similar_anchors(
        anchor_type="cognitive_episode",
        context_features={
            "trigger": "x",
            "tool_names": ["a"],
            "outcome_status": "completed",
            "error_kind": "none",
            "summary": "exactly the same",
        },
    )
    ids = [m["anchor_id"] for m in matches]
    assert ids.index("fresh") < ids.index("aged")


def test_find_similar_returns_empty_when_no_match(isolated_runtime) -> None:
    from core.services.emotional_memory_engine import find_similar_anchors

    matches = find_similar_anchors(
        anchor_type="cognitive_episode",
        context_features={"trigger": "any", "tool_names": [], "summary": "anything"},
    )
    assert matches == []
