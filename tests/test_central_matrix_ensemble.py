"""Tests: Matrix Ensemble — central_matrix_ensemble.py (Spec F)"""

from core.services.central_matrix_ensemble import build_matrix_ensemble_section


def test_ensemble_returns_string_or_none() -> None:
    """build_matrix_ensemble_section must return str (with or without labels) or None."""
    result = build_matrix_ensemble_section()
    assert result is None or isinstance(result, str)


def test_ensemble_contains_active_characters_when_present() -> None:
    """When any character is active, their label must appear in output."""
    result = build_matrix_ensemble_section()
    if result and result != "Alle Matrix-karakterer er stille lige nu.":
        assert "[" in result  # at least one [🎭 label]


def test_ensemble_no_leaked_content() -> None:
    """Ensemble must never leak private brain content — only labels and one-liners."""
    result = build_matrix_ensemble_section()
    if result is None:
        return
    # Labels only — no raw data dumps
    assert "private_brain" not in result
    assert "{" not in result or "label" in result  # only dict-like for labels
