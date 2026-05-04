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
