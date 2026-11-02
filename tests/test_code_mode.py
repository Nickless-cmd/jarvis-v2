"""The engineering contract belongs to code mode and nowhere else."""
from __future__ import annotations

from core.services.prompt_sections.code_mode import section
from core.services.prompt_sections.chat_mode import (
    _visible_mode_orientation_instruction,
)
from core.tools.tool_scoping import tool_scope


def test_code_contract_covers_the_end_to_end_working_model() -> None:
    with tool_scope("code"):
        text = section(compact=False) or ""

    expected = (
        "Opgaven betyder handling",
        "Undersøg før du ændrer",
        "Ret grundårsagen",
        "Fortsæt til et færdigt resultat",
        "Beskyt worktree og data",
        "Verificér efter risiko",
        "Planer og løfter skal lukkes",
        "Review er fund før resumé",
        "Aflever beviseligt",
    )
    for phrase in expected:
        assert phrase in text


def test_code_contract_is_injected_only_in_code_scope() -> None:
    with tool_scope("code"):
        code = _visible_mode_orientation_instruction(compact=False) or ""
    with tool_scope("chat"):
        chat = _visible_mode_orientation_instruction(compact=False) or ""
    with tool_scope(""):
        unbound = _visible_mode_orientation_instruction(compact=False) or ""

    assert "## Code mode: arbejdsadfærd" in code
    assert "Fortsæt til et færdigt resultat" in code
    assert "## Code mode: arbejdsadfærd" not in chat
    assert "Fortsæt til et færdigt resultat" not in chat
    assert "## Code mode: arbejdsadfærd" not in unbound
    assert "Fortsæt til et færdigt resultat" not in unbound


def test_compact_code_contract_keeps_the_critical_path() -> None:
    with tool_scope("code"):
        text = _visible_mode_orientation_instruction(compact=True) or ""

    assert "Opgaven betyder handling" in text
    assert "Undersøg før du ændrer" in text
    assert "Beskyt worktree og data" in text
    assert "Verificér efter risiko" in text
    assert "Aflever beviseligt" in text


def test_code_contract_function_returns_none_outside_code() -> None:
    with tool_scope("chat"):
        assert section(compact=False) is None
    with tool_scope(""):
        assert section(compact=False) is None
