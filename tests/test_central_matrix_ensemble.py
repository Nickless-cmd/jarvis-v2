"""Tests: Matrix Ensemble — central_matrix_ensemble.py (Spec F)"""

from core.services.central_matrix_ensemble import (
    build_matrix_ensemble_prompt_section,
    build_matrix_signoff_section,
)


def test_ensemble_returns_string_or_none() -> None:
    """build_matrix_ensemble_prompt_section must return str or None."""
    result = build_matrix_ensemble_prompt_section()
    assert result is None or isinstance(result, str)


def test_ensemble_contains_active_characters_when_present() -> None:
    """When any character is active, their label must appear in output."""
    result = build_matrix_ensemble_prompt_section()
    if result and result != "Alle Matrix-karakterer er stille lige nu.":
        assert "[" in result  # at least one [🎭 label]


def test_ensemble_no_leaked_content() -> None:
    """Ensemble must never leak private brain content — only labels and one-liners."""
    result = build_matrix_ensemble_prompt_section()
    if result is None:
        return
    # Labels only — no raw data dumps
    assert "private_brain" not in result


def test_signoff_returns_string_or_none() -> None:
    """build_matrix_signoff_section must return str starting with MATRIX SIGN-OFF or None."""
    result = build_matrix_signoff_section()
    assert result is None or (isinstance(result, str) and result.startswith("MATRIX SIGN-OFF:"))


def test_signoff_contains_label_when_active() -> None:
    """When a character is active, the sign-off must include their label."""
    result = build_matrix_signoff_section()
    if result is not None:
        assert "[" in result and "]" in result  # contains [emoji Name]
