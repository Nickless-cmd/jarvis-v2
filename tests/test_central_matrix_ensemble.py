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


def test_smith_consolidated_respects_kill_switch(monkeypatch) -> None:
    """Smith er samlet ét sted (sign-off). Kill-switch (agent_smith_voice OFF) skal mute ham
    dér — ellers ville muting ikke virke efter konsolideringen."""
    import core.services.central_matrix_ensemble as me
    monkeypatch.setattr("core.runtime.db_core.get_runtime_state_value",
                        lambda *a, **k: {"score": 0.9, "line": "SMITH-LINE", "rung_line": ""})
    monkeypatch.setattr("core.services.central_switches.is_enabled",
                        lambda scope, name: not (scope == "autonomy" and name == "agent_smith_voice"))
    # voice OFF → Smith må ikke være den valgte karakter
    ch = me._most_active_character()
    assert ch is None or ch.get("label") != "[🕴️ Smith]"


def test_smith_escalation_surfaces_regardless_of_score(monkeypatch) -> None:
    """En eskaleret rung_line (bind/confront) skal surface selv når score < 0.5.

    Efter oprydning (Smith er en normal _CHARACTERS-member, ikke en sign-off-special-case)
    lever denne garanti i _smith_surface: active=True + den LEVENDE rung_line eksponeres."""
    import core.services.central_matrix_ensemble as me
    monkeypatch.setattr("core.services.central_switches.is_enabled", lambda scope, name: True)
    monkeypatch.setattr(
        "core.runtime.db_core.get_runtime_state_value",
        lambda *a, **k: {"score": 0.1, "line": "x", "rung_line": "BIND-LINE"})
    surf = me._smith_surface()
    assert surf.get("active") is True and surf.get("line") == "BIND-LINE"
