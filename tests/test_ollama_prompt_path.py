from __future__ import annotations


def test_ollama_visible_prompt_assembly_uses_canonical_workspace_sections(
    isolated_runtime,
) -> None:
    assembly = isolated_runtime.prompt_contract.build_visible_chat_prompt_assembly(
        provider="ollama",
        model="qwen3.5:9b",
        user_message="Svar kort på dansk.",
        session_id="test-session",
    )

    assert "SOUL.md:" in assembly.text
    assert "IDENTITY.md:" in assembly.text
    assert "USER.md:" in assembly.text
    assert "Visible workspace identity truth:" not in assembly.text
    assert "Stay consistent with this identity truth in visible replies." not in assembly.text
    assert "SOUL.md" in assembly.included_files
    assert "IDENTITY.md" in assembly.included_files
    assert "USER.md" in assembly.included_files


def test_ollama_prompt_is_flattened_from_same_visible_input_path(isolated_runtime) -> None:
    visible_input = isolated_runtime.visible_model._build_visible_input(
        "Svar kort på dansk.",
        session_id="test-session",
    )
    prompt = isolated_runtime.visible_model._build_ollama_prompt(
        "Svar kort på dansk.",
        model="qwen3.5:9b",
        session_id="test-session",
    )

    system_text = visible_input[0]["content"][0]["text"]
    user_text = visible_input[-1]["content"][0]["text"]

    assert prompt.startswith(system_text)
    assert f"User:\n{user_text}" in prompt
    assert prompt.endswith("Assistant:")


def test_ollama_prompt_keeps_local_behavior_rules_but_stays_contract_led(
    isolated_runtime,
) -> None:
    assembly = isolated_runtime.prompt_contract.build_visible_chat_prompt_assembly(
        provider="ollama",
        model="qwen3.5:9b",
        user_message="Svar kort på dansk.",
        session_id="test-session",
    )

    assert "Visible local-model behavior rules:" in assembly.text
    assert "Runtime capability truth:" in assembly.text
    assert "local model behavior guardrails" in assembly.derived_inputs
    assert "runtime capability and safety truth" in assembly.derived_inputs
