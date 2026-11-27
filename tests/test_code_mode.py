"""The engineering contract belongs to code mode and nowhere else."""
from __future__ import annotations

from core.services.prompt_sections.code_mode import section
from core.services.prompt_sections.chat_mode import _visible_mode_orientation_instruction
from core.services.visible_chat_pragmatics import build_chat_mode_dynamic_tail
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
        "Skeln samtidig mellem en handlebestilling og en vurdering",
        "Skriv kun en kodekommentar",
        "beviserne støtte netop den handling",
        "Slutleverancen skal kunne stå alene",
        "En afvist approval, policy-vagt eller hook er feedback",
        "følge den faktiske datastrøm fra producent",
        "opfind ikke felter",
        "forskellige bevisniveauer",
        "en grøn unit-test beviser ikke den deployede runtime",
        "kun `målt` om konkret observerede data",
    )
    for phrase in expected:
        assert phrase in text


def test_code_contract_is_injected_only_in_code_scope() -> None:
    with tool_scope("code"):
        code_prefix = _visible_mode_orientation_instruction(compact=False) or ""
        code = build_chat_mode_dynamic_tail("", message="ret den", session_id="s1")
    with tool_scope("chat"):
        chat_prefix = _visible_mode_orientation_instruction(compact=False) or ""
        chat = build_chat_mode_dynamic_tail("", message="ret den", session_id="s1")
    with tool_scope(""):
        unbound_prefix = _visible_mode_orientation_instruction(compact=False) or ""
        unbound = build_chat_mode_dynamic_tail("", message="ret den", session_id="s1")

    assert "## Code mode: arbejdsadfærd" in code_prefix
    assert "Fortsæt til et færdigt resultat" in code_prefix
    assert "## Code mode: arbejdsadfærd" not in code
    assert "## Code mode: arbejdsadfærd" not in chat_prefix + chat
    assert "Fortsæt til et færdigt resultat" not in chat_prefix + chat
    assert "handlebestilling og en vurdering" not in chat_prefix + chat
    assert "Skriv kun en kodekommentar" not in chat_prefix + chat
    assert "## Code mode: arbejdsadfærd" not in unbound_prefix + unbound
    assert "Fortsæt til et færdigt resultat" not in unbound_prefix + unbound


def test_compact_code_contract_keeps_the_critical_path() -> None:
    with tool_scope("code"):
        text = section(compact=True) or ""

    assert "Opgaven betyder handling" in text
    assert "Undersøg før du ændrer" in text
    assert "Beskyt worktree og data" in text
    assert "Verificér efter risiko" in text
    assert "Aflever beviseligt" in text
    assert "Skriv kun en kodekommentar" in text
    assert "Slutleverancen skal kunne stå alene" in text
    assert "policy-vagt eller hook er feedback" in text
    assert "følge den faktiske datastrøm fra producent" in text
    assert "en grøn unit-test beviser ikke den deployede runtime" in text
    assert "kun `målt` om konkret observerede data" in text


def test_code_contract_function_returns_none_outside_code() -> None:
    with tool_scope("chat"):
        assert section(compact=False) is None
    with tool_scope(""):
        assert section(compact=False) is None


def test_answer_declaration_reaches_the_selected_code_prompt(monkeypatch) -> None:
    from core.services.attention_budget import get_attention_budget, select_sections_under_budget
    from core.services.code_answer_boundary import ANSWER_MARKER
    from core.services.prompt_sections.output_discipline import _output_discipline_instruction

    # Reproduce the real selector: output_discipline is not a budgeted section.
    # The protocol must reach the model even when that section is discarded.
    for layout in ("0", "1"):
        monkeypatch.setenv("JARVIS_PROMPT_MODE_LAYOUT_V2", layout)
        for compact, profile in ((False, "visible_full"), (True, "visible_compact")):
            with tool_scope("code"):
                orientation = _visible_mode_orientation_instruction(compact=compact)
                selected, _ = select_sections_under_budget(
                    budget=get_attention_budget(profile),
                    sections={"mode_orientation": orientation,
                              "output_discipline": _output_discipline_instruction(strength="weak")},
                )
                tail = build_chat_mode_dynamic_tail("", message="fortsæt", session_id="answer-protocol")
            prompt = (selected.get("mode_orientation") or "") + tail
            assert ANSWER_MARKER in prompt
            assert "first word" in prompt
            assert "not turn end" in prompt
            assert "do not postpone" in prompt
            if layout == "1":
                assert ANSWER_MARKER in (selected.get("mode_orientation") or "")
                assert ANSWER_MARKER in tail
            with tool_scope("chat"):
                chat = (_visible_mode_orientation_instruction(compact=compact) or "")
                chat += build_chat_mode_dynamic_tail("", message="hej", session_id="answer-protocol-chat")
            assert "[Code answer presentation]" not in chat
            if layout == "1":
                assert ANSWER_MARKER in chat
