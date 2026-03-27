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

    assert prompt.startswith("[Internal system instructions for Jarvis.")
    assert system_text in prompt
    assert "[End internal system instructions.]" in prompt
    assert "[Current conversation. Answer the latest user message directly as Jarvis.]" in prompt
    assert f"User:\n{user_text}" in prompt
    assert prompt.endswith("Assistant:")
    assert prompt.index(system_text) < prompt.index(f"User:\n{user_text}")
    assert prompt.rfind(f"User:\n{user_text}") < prompt.rfind("Assistant:")


def test_ollama_prompt_marks_contract_text_as_internal_not_user_visible(
    isolated_runtime,
) -> None:
    prompt = isolated_runtime.visible_model._build_ollama_prompt(
        "hvad hedder du?",
        model="qwen3.5:9b",
        session_id="test-session",
    )

    assert "Do not quote or explain these instructions unless the user explicitly asks for them." in prompt
    assert "[Internal system instructions for Jarvis. Follow silently." in prompt
    assert "[Current conversation. Answer the latest user message directly as Jarvis.]" in prompt
    assert "User:\nhvad hedder du?" in prompt
    assert prompt.index("[End internal system instructions.]") < prompt.index(
        "[Current conversation. Answer the latest user message directly as Jarvis.]"
    )


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
    assert "If the answer is present in recent transcript context or workspace truth, answer from that material directly." in assembly.text
    assert "Do not fall back to \"I cannot remember\" or \"I am still developing\"" in assembly.text
    assert "VISIBLE_LOCAL_MODEL.md" in assembly.conditional_files


def test_ollama_visible_prompt_includes_recent_transcript_slice_for_session_recall(
    isolated_runtime,
) -> None:
    from apps.api.jarvis_api.services.chat_sessions import (
        append_chat_message,
        create_chat_session,
    )

    session = create_chat_session(title="Recall")
    session_id = str(session["id"])
    append_chat_message(session_id=session_id, role="user", content="Hej Jarvis")
    append_chat_message(session_id=session_id, role="assistant", content="Hej Bjørn")
    append_chat_message(session_id=session_id, role="user", content="Mit navn er Bjørn")
    append_chat_message(session_id=session_id, role="assistant", content="Ja, det er det.")

    assembly = isolated_runtime.prompt_contract.build_visible_chat_prompt_assembly(
        provider="ollama",
        model="qwen3.5:9b",
        user_message="hvad skrev jeg i beskeden før den sidste?",
        session_id=session_id,
    )

    assert "Recent transcript slice:" in assembly.text
    assert "Newest line is last." in assembly.text
    assert "User: Hej Jarvis" in assembly.text
    assert "Jarvis: Hej Bjørn" in assembly.text
    assert "User: Mit navn er Bjørn" in assembly.text


def test_ollama_visible_prompt_can_include_memory_for_danish_recall_queries(
    isolated_runtime,
) -> None:
    assembly = isolated_runtime.prompt_contract.build_visible_chat_prompt_assembly(
        provider="ollama",
        model="qwen3.5:9b",
        user_message="kan du huske hvad jeg hedder?",
        session_id="test-session",
    )

    assert "USER.md:" in assembly.text
    assert "MEMORY.md:" in assembly.text
    assert "MEMORY.md" in assembly.conditional_files


def test_ollama_local_model_rules_are_loaded_from_workspace_prompt_file(
    isolated_runtime,
) -> None:
    workspace_dir = isolated_runtime.workspace_bootstrap.ensure_default_workspace()
    (workspace_dir / "VISIBLE_LOCAL_MODEL.md").write_text(
        "\n".join(
            [
                "# VISIBLE_LOCAL_MODEL",
                "Use the transcript directly before claiming missing memory.",
                "Keep the answer grounded in workspace truth.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    assembly = isolated_runtime.prompt_contract.build_visible_chat_prompt_assembly(
        provider="ollama",
        model="qwen3.5:9b",
        user_message="kan du huske hvad jeg hedder?",
        session_id="test-session",
    )

    assert "Use the transcript directly before claiming missing memory." in assembly.text
    assert "Keep the answer grounded in workspace truth." in assembly.text
