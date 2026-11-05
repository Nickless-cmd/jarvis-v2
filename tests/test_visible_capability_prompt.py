from __future__ import annotations


def test_visible_prompt_surfaces_tool_calling_instructions(isolated_runtime) -> None:
    """Den AKTIVE gren skal bære værktøjs-kontrakten.

    Målt 5/11-2026: testen krævede legacy-ordlyden («Runtime tool calling:»,
    «auto-approved», «user approval»), som kun findes i den gren
    `mode_layout_v2_enabled()` erstattede (commit 4f5f722a2). Den målte altså
    kode der ikke kører. Kravene nedenfor er dem v2-grenen faktisk garanterer.
    """
    prompt_contract = isolated_runtime.prompt_contract

    instruction = prompt_contract._visible_capability_truth_instruction(compact=False)

    assert instruction is not None
    assert "Runtime capability truth:" in instruction
    assert "native tools exposed in this request are authoritative" in instruction
    assert "never simulate a tool call in prose" in instruction
    assert "is not success" in instruction


def test_legacy_capability_instruction_still_carries_its_contract() -> None:
    """Legacy-grenen er stadig kode der kan køre — dens kontrakt må ikke rådne.

    Uden denne test ville et brud i legacy-grenen være uset, fordi den aktive
    gren er v2. Testen kalder legacy-funktionen direkte, ikke gennem flaget.
    """
    from core.services.prompt_sections.visible_capability_truth import (
        _legacy_capability_truth_instruction,
    )

    text = _legacy_capability_truth_instruction(compact=False)

    assert "Runtime tool calling:" in text
    assert "native function calling" in text
    assert "read_file" in text
    assert "auto-approved" in text or "auto-approve" in text
    assert "user approval" in text


def test_visible_prompt_assembly_includes_tool_info(isolated_runtime) -> None:
    prompt_contract = isolated_runtime.prompt_contract

    assembly = prompt_contract.build_visible_chat_prompt_assembly(
        provider="openai",
        model="gpt-5",
        user_message="Kan du bruge tools her?",
        session_id=None,
    )

    assert "read_file" in assembly.text
    assert "search" in assembly.text
    assert "bash" in assembly.text
