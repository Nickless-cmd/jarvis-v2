from __future__ import annotations


def test_visible_prompt_surfaces_callable_and_gated_capabilities(isolated_runtime) -> None:
    prompt_contract = isolated_runtime.prompt_contract

    instruction = prompt_contract._visible_capability_truth_instruction(compact=False)

    assert instruction is not None
    assert "Runtime capability truth:" in instruction
    assert '<capability-call id="capability_id" />' in instruction
    assert '<capability-call id="capability_id" command_text="pwd" />' in instruction
    assert "emit exactly one capability-call line and no surrounding prose" in instruction
    assert "capability-call tag is authoritative" in instruction
    assert "Do not emit JSON or pseudo-JSON tool calls." in instruction
    assert "tool:read-workspace-user-profile" in instruction
    assert "tool:search-workspace-memory-continuity" in instruction
    assert "tool:read-repository-readme" in instruction
    assert "tool:read-external-file-by-path" in instruction
    assert "tool:run-non-destructive-command" in instruction
    assert "tool:propose-workspace-memory-update" in instruction
    assert "tool:propose-external-repo-file-update" in instruction
    assert "workspace_read=allowed" in instruction
    assert "external_read=allowed" in instruction
    assert "non_destructive_exec=allowed" in instruction
    assert "workspace_write=explicit-approval-required" in instruction


def test_visible_prompt_assembly_keeps_text_capability_contract(isolated_runtime) -> None:
    prompt_contract = isolated_runtime.prompt_contract

    assembly = prompt_contract.build_visible_chat_prompt_assembly(
        provider="openai",
        model="gpt-5",
        user_message="Kan du bruge tools her?",
        session_id=None,
    )

    assert '<capability-call id="capability_id" />' in assembly.text
    assert '<capability-call id="capability_id" command_text="pwd" />' in assembly.text
    assert "tool:read-workspace-user-profile" in assembly.text
    assert "tool:read-external-file-by-path" in assembly.text
    assert "tool:run-non-destructive-command" in assembly.text
