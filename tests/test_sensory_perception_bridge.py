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
