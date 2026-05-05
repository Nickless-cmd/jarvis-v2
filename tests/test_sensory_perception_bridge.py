from __future__ import annotations


def test_shingle_returns_word_ngrams(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _shingle

    tokens = _shingle("the quick brown fox", n=3)
    assert "the quick brown" in tokens
    assert "quick brown fox" in tokens
    assert len(tokens) == 2


def test_shingle_handles_short_text(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _shingle

    tokens = _shingle("hi there", n=3)
    assert tokens == {"hi", "there"}


def test_shingle_returns_empty_for_empty_text(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _shingle

    assert _shingle("") == set()
    assert _shingle("   ") == set()


def test_jaccard_identical_sets_returns_1(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _jaccard

    a = {"a", "b", "c"}
    assert _jaccard(a, a) == 1.0


def test_jaccard_disjoint_sets_returns_0(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _jaccard

    assert _jaccard({"a", "b"}, {"c", "d"}) == 0.0


def test_jaccard_partial_overlap(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _jaccard

    score = _jaccard({"a", "b"}, {"b", "c"})
    assert abs(score - 1 / 3) < 1e-6


def test_jaccard_both_empty_returns_0(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _jaccard

    assert _jaccard(set(), set()) == 0.0


def test_mode_returns_most_common_value(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _mode

    assert _mode(["a", "b", "a", "c"]) == "a"


def test_mode_returns_first_on_tie(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _mode

    result = _mode(["a", "b", "a", "b"])
    assert result == "a"


def test_mode_handles_empty_list(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _mode

    assert _mode([]) is None


def test_aggregate_baseline_uses_mood_mode(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _aggregate_baseline

    records = [
        {"mood_tone": "rolig", "content": "lyset er varmt", "metadata": {}},
        {"mood_tone": "rolig", "content": "det er stille", "metadata": {}},
        {"mood_tone": "travl", "content": "der er gang i den", "metadata": {}},
    ]
    baseline = _aggregate_baseline(records)
    assert baseline["mood"] == "rolig"
    assert len(baseline["records"]) == 3


def test_aggregate_baseline_unions_content_tokens(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _aggregate_baseline

    records = [
        {"mood_tone": "x", "content": "the quick brown fox jumped", "metadata": {}},
        {"mood_tone": "x", "content": "lazy dog sleeping quietly today", "metadata": {}},
    ]
    baseline = _aggregate_baseline(records)
    assert "the quick brown" in baseline["content_tokens"]
    assert "lazy dog sleeping" in baseline["content_tokens"]


def test_aggregate_baseline_unions_metadata(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _aggregate_baseline

    records = [
        {"mood_tone": None, "content": "", "metadata": {"category": "silence"}},
        {"mood_tone": None, "content": "", "metadata": {"category": "talk", "amplitude": 0.3}},
    ]
    baseline = _aggregate_baseline(records)
    assert baseline["metadata"]["category"] == {"silence", "talk"}
    assert baseline["metadata"]["amplitude"] == {"0.3"}


def test_aggregate_baseline_filters_empty_moods(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _aggregate_baseline

    records = [
        {"mood_tone": None, "content": "", "metadata": {}},
        {"mood_tone": "rolig", "content": "", "metadata": {}},
        {"mood_tone": "", "content": "", "metadata": {}},
    ]
    baseline = _aggregate_baseline(records)
    assert baseline["mood"] == "rolig"


def test_recent_baseline_returns_last_three_excluding_current(isolated_runtime) -> None:
    from core.runtime.db_sensory import insert_sensory_memory, list_sensory_memories
    from core.services.sensory_perception_bridge import _recent_baseline

    for i, mood in enumerate(["rolig", "rolig", "travl", "rolig", "kaotisk"]):
        insert_sensory_memory(
            modality="atmosphere",
            content=f"sample {i}",
            mood_tone=mood,
            metadata={},
        )
    rows = list_sensory_memories(modality="atmosphere", limit=10)
    assert len(rows) == 5
    current = rows[0]

    baseline = _recent_baseline("atmosphere", current)
    assert len(baseline["records"]) == 3
    assert all(r["id"] != current["id"] for r in baseline["records"])


def test_recent_baseline_returns_empty_for_first_record(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _recent_baseline

    fake_record = {
        "id": "nonexistent",
        "modality": "atmosphere",
        "content": "first one",
        "mood_tone": "rolig",
        "metadata": {},
        "timestamp": "2026-05-04T12:00:00+00:00",
    }
    baseline = _recent_baseline("atmosphere", fake_record)
    assert baseline["records"] == []
    assert baseline["mood"] is None
    assert baseline["content_tokens"] == set()


def test_time_of_day_baseline_returns_records_in_window(isolated_runtime) -> None:
    from datetime import UTC, datetime, timedelta
    from core.runtime.db_sensory import insert_sensory_memory
    from core.services.sensory_perception_bridge import _time_of_day_baseline

    base = datetime(2026, 5, 4, 14, 0, tzinfo=UTC)
    in_window_times = [
        base - timedelta(days=1, minutes=30),
        base - timedelta(days=2),
        base - timedelta(days=3, hours=1),
    ]
    out_of_window_times = [
        base - timedelta(days=1, hours=4),
        base - timedelta(days=2, hours=6),
    ]
    for ts in in_window_times + out_of_window_times:
        insert_sensory_memory(
            modality="visual",
            content=f"snapshot at {ts.isoformat()}",
            mood_tone="rolig",
            metadata={},
            timestamp=ts.isoformat(),
        )

    current = {
        "id": "current-uuid",
        "modality": "visual",
        "content": "now",
        "mood_tone": "rolig",
        "metadata": {},
        "timestamp": base.isoformat(),
    }
    baseline = _time_of_day_baseline("visual", current)
    assert baseline is not None
    assert len(baseline["records"]) == 3


def test_time_of_day_baseline_returns_none_when_under_threshold(
    isolated_runtime,
) -> None:
    from datetime import UTC, datetime, timedelta
    from core.runtime.db_sensory import insert_sensory_memory
    from core.services.sensory_perception_bridge import _time_of_day_baseline

    base = datetime(2026, 5, 4, 14, 0, tzinfo=UTC)
    for ts in [base - timedelta(days=1), base - timedelta(days=2)]:
        insert_sensory_memory(
            modality="visual", content="x", mood_tone="rolig", metadata={},
            timestamp=ts.isoformat(),
        )

    current = {
        "id": "current",
        "modality": "visual",
        "content": "now",
        "mood_tone": "rolig",
        "metadata": {},
        "timestamp": base.isoformat(),
    }
    assert _time_of_day_baseline("visual", current) is None


def test_build_baseline_visual_falls_back_to_recent_when_window_thin(
    isolated_runtime,
) -> None:
    from datetime import UTC, datetime, timedelta
    from core.runtime.db_sensory import insert_sensory_memory
    from core.services.sensory_perception_bridge import _build_baseline

    base = datetime(2026, 5, 4, 14, 0, tzinfo=UTC)
    for ts in [base - timedelta(hours=10), base - timedelta(hours=20)]:
        insert_sensory_memory(
            modality="visual", content="x", mood_tone="rolig", metadata={},
            timestamp=ts.isoformat(),
        )

    current = {
        "id": "current", "modality": "visual", "content": "now",
        "mood_tone": "rolig", "metadata": {}, "timestamp": base.isoformat(),
    }
    baseline = _build_baseline("visual", current)
    assert baseline is not None
    assert len(baseline["records"]) == 2


def test_build_baseline_atmosphere_uses_recent_directly(isolated_runtime) -> None:
    from core.runtime.db_sensory import insert_sensory_memory
    from core.services.sensory_perception_bridge import _build_baseline

    for i in range(3):
        insert_sensory_memory(
            modality="atmosphere", content=f"x{i}", mood_tone="rolig", metadata={},
        )

    fake_current = {
        "id": "fake-current", "modality": "atmosphere", "content": "z",
        "mood_tone": "rolig", "metadata": {}, "timestamp": "2026-05-04T12:00:00+00:00",
    }
    baseline = _build_baseline("atmosphere", fake_current)
    assert baseline is not None
    assert len(baseline["records"]) == 3


def test_metadata_changed_audio_category_shift(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _metadata_changed

    new_md = {"category": "talk", "amplitude": 0.3}
    baseline_md = {"category": {"silence"}, "amplitude": {"0.1"}}
    assert _metadata_changed(new_md, baseline_md, "audio") is True


def test_metadata_changed_audio_same_category(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _metadata_changed

    new_md = {"category": "talk", "amplitude": 0.5}
    baseline_md = {"category": {"talk"}, "amplitude": {"0.3"}}
    assert _metadata_changed(new_md, baseline_md, "audio") is False


def test_metadata_changed_visual_ignores_prompt_rotation(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _metadata_changed

    new_md = {"vision_prompt_index": 2}
    baseline_md = {"vision_prompt_index": {"0", "1"}}
    assert _metadata_changed(new_md, baseline_md, "visual") is False


def test_metadata_changed_atmosphere_any_value_shift(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _metadata_changed

    new_md = {"weather": "rainy"}
    baseline_md = {"weather": {"sunny"}}
    assert _metadata_changed(new_md, baseline_md, "atmosphere") is True


def test_metadata_changed_atmosphere_new_key(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _metadata_changed

    new_md = {"weather": "sunny", "occupants": 2}
    baseline_md = {"weather": {"sunny"}}
    assert _metadata_changed(new_md, baseline_md, "atmosphere") is True


def test_metadata_changed_returns_false_for_empty(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _metadata_changed

    assert _metadata_changed({}, {}, "audio") is False
    assert _metadata_changed({}, {}, "visual") is False
    assert _metadata_changed({}, {}, "atmosphere") is False
