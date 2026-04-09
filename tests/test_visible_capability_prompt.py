from __future__ import annotations


def test_visible_prompt_surfaces_tool_calling_instructions(isolated_runtime) -> None:
    prompt_contract = isolated_runtime.prompt_contract

    instruction = prompt_contract._visible_capability_truth_instruction(compact=False)

    assert instruction is not None
    assert "Runtime tool calling:" in instruction
    assert "native function calling" in instruction
    assert "read_file" in instruction
    assert "auto-approved" in instruction or "auto-approve" in instruction
    assert "user approval" in instruction


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
