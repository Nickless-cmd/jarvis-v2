from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4


def _apply_memory_candidate(
    isolated_runtime,
    *,
    canonical_key: str,
    summary: str,
    proposed_value: str,
) -> None:
    db = isolated_runtime.db
    candidate_workflow = __import__(
        "core.identity.candidate_workflow",
        fromlist=["approve_runtime_contract_candidate", "apply_runtime_contract_candidate"],
    )

    now = datetime.now(UTC).isoformat()
    candidate = db.upsert_runtime_contract_candidate(
        candidate_id=f"candidate-{uuid4().hex}",
        candidate_type="memory_promotion",
        target_file="MEMORY.md",
        status="proposed",
        source_kind="runtime-derived-support",
        source_mode="test-runtime",
        actor="runtime:test",
        session_id="test-session",
        run_id="test-run",
        canonical_key=canonical_key,
        summary=summary,
        reason="Validation applied memory candidate",
        evidence_summary="candidate evidence",
        support_summary="candidate support",
        confidence="high",
        evidence_class="runtime_support_only",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation candidate status",
        proposed_value=proposed_value,
        write_section="## Curated Memory",
    )
    approved = candidate_workflow.approve_runtime_contract_candidate(str(candidate["candidate_id"]))
    candidate_workflow.apply_runtime_contract_candidate(str(approved["candidate_id"]))


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


def test_visible_prompt_relevance_interface_keeps_generic_compact_chat_bounded(
    isolated_runtime,
) -> None:
    decision = isolated_runtime.prompt_contract.build_prompt_relevance_decision(
        "Svar kort på dansk.",
        mode="visible_chat",
        compact=True,
    )

    assert decision.mode == "visible_chat"
    assert decision.memory_relevant is False
    assert decision.guidance_relevant is False
    assert decision.transcript_relevant is False
    assert decision.continuity_relevant is False
    assert decision.include_memory is False
    assert decision.include_guidance is False
    assert decision.include_transcript is True
    assert decision.include_continuity is False
    assert decision.include_support_signals is False


def test_visible_prompt_relevance_interface_keeps_recall_queries_memory_aware(
    isolated_runtime,
) -> None:
    decision = isolated_runtime.prompt_contract.build_prompt_relevance_decision(
        "kan du huske hvad jeg hedder?",
        mode="visible_chat",
        compact=True,
    )

    assert decision.mode == "visible_chat"
    assert decision.memory_relevant is True
    assert decision.guidance_relevant is False
    assert decision.transcript_relevant is True
    assert decision.continuity_relevant is False
    assert decision.include_memory is True
    assert decision.include_guidance is False
    assert decision.include_transcript is True
    assert decision.include_continuity is False
    assert decision.include_support_signals is True


def test_visible_prompt_relevance_interface_keeps_heuristic_fallback_when_nl_is_missing(
    isolated_runtime,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        isolated_runtime.prompt_contract,
        "_bounded_nl_relevance_backend",
        lambda **_: None,
    )

    decision = isolated_runtime.prompt_contract.build_prompt_relevance_decision(
        "kan du huske hvad jeg hedder?",
        mode="visible_chat",
        compact=True,
    )

    assert decision.memory_relevant is True
    assert decision.transcript_relevant is True
    assert decision.include_memory is True
    assert decision.include_support_signals is True


def test_visible_prompt_relevance_interface_can_use_bounded_nl_backend_for_paraphrase(
    isolated_runtime,
    monkeypatch,
) -> None:
    assert (
        isolated_runtime.prompt_contract._should_include_memory(
            "what are we collaborating around lately?",
            mode="visible_chat",
        )
        is False
    )

    monkeypatch.setattr(
        isolated_runtime.prompt_contract,
        "_bounded_nl_relevance_backend",
        lambda **_: type(
            "MockRelevance",
            (),
            {
                "memory_relevant": True,
                "guidance_relevant": False,
                "transcript_relevant": True,
                "continuity_relevant": False,
                "support_signals_relevant": True,
            },
        )(),
    )

    decision = isolated_runtime.prompt_contract.build_prompt_relevance_decision(
        "what are we collaborating around lately?",
        mode="visible_chat",
        compact=True,
    )

    assert decision.memory_relevant is True
    assert decision.transcript_relevant is True
    assert decision.include_memory is True
    assert decision.include_support_signals is True


def test_bounded_nl_relevance_backend_loads_workspace_prompt_and_parses_json(
    isolated_runtime,
    monkeypatch,
) -> None:
    backend = __import__(
        "apps.api.jarvis_api.services.prompt_relevance_backend",
        fromlist=["run_bounded_nl_prompt_relevance"],
    )
    workspace_dir = isolated_runtime.workspace_bootstrap.ensure_default_workspace()
    (workspace_dir / "VISIBLE_RELEVANCE.md").write_text(
        "\n".join(
            [
                "# VISIBLE_RELEVANCE",
                "Use memory_relevant for collaboration-paraphrase questions.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    captured: dict[str, object] = {}

    monkeypatch.setattr(
        backend,
        "resolve_provider_router_target",
        lambda lane: {
            "active": lane == "local",
            "provider": "ollama" if lane == "local" else None,
            "base_url": "http://127.0.0.1:11434" if lane == "local" else None,
        },
    )

    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self) -> bytes:
            return json.dumps(
                {
                    "response": json.dumps(
                        {
                            "memory_relevant": True,
                            "guidance_relevant": False,
                            "transcript_relevant": True,
                            "continuity_relevant": False,
                            "support_signals_relevant": True,
                            "confidence": "medium",
                        }
                    )
                }
            ).encode("utf-8")

    def _fake_urlopen(req, timeout):
        captured["timeout"] = timeout
        captured["payload"] = json.loads(req.data.decode("utf-8"))
        return _FakeResponse()

    monkeypatch.setattr(backend.urllib_request, "urlopen", _fake_urlopen)

    result = backend.run_bounded_nl_prompt_relevance(
        text="what are we collaborating around lately?",
        mode="visible_chat",
        compact=True,
        workspace_dir=workspace_dir,
    )

    assert result is not None
    assert result.backend == "bounded-local-ollama"
    assert result.memory_relevant is True
    assert result.transcript_relevant is True
    assert result.support_signals_relevant is True
    assert result.confidence == "medium"
    assert captured["timeout"] == backend.RELEVANCE_TIMEOUT_SECONDS
    assert "Use memory_relevant for collaboration-paraphrase questions." in str(
        captured["payload"]["prompt"]
    )


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
    assert "Visible chat guidance rules:" in assembly.text
    assert "Runtime capability truth:" in assembly.text
    assert "local model behavior guardrails" in assembly.derived_inputs
    assert "runtime capability and safety truth" in assembly.derived_inputs
    assert "visible chat guidance rules" in assembly.derived_inputs
    assert "If the answer is present in recent transcript context or workspace truth, answer from that material directly." in assembly.text
    assert "Do not fall back to \"I cannot remember\" or \"I am still developing\"" in assembly.text
    assert "VISIBLE_LOCAL_MODEL.md" in assembly.conditional_files
    assert "VISIBLE_CHAT_RULES.md" in assembly.conditional_files


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
    assert "Use the recent transcript slice as recent context, not as stable memory." in assembly.text


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


def test_visible_chat_guidance_rules_are_loaded_from_workspace_prompt_file(
    isolated_runtime,
) -> None:
    workspace_dir = isolated_runtime.workspace_bootstrap.ensure_default_workspace()
    (workspace_dir / "VISIBLE_CHAT_RULES.md").write_text(
        "\n".join(
            [
                "# VISIBLE_CHAT_RULES",
                "Use transcript context before generic continuity disclaimers.",
                "Treat guidance files as hints, not authority.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    assembly = isolated_runtime.prompt_contract.build_visible_chat_prompt_assembly(
        provider="ollama",
        model="qwen3.5:9b",
        user_message="hvad skrev jeg i beskeden før den sidste?",
        session_id="test-session",
    )

    assert "Use transcript context before generic continuity disclaimers." in assembly.text
    assert "Treat guidance files as hints, not authority." in assembly.text


def test_ollama_visible_prompt_can_include_relevant_applied_project_anchor_memory(
    isolated_runtime,
) -> None:
    _apply_memory_candidate(
        isolated_runtime,
        canonical_key="workspace-memory:remembered-fact:project-anchor",
        summary="A bounded remembered fact may be worth carrying into MEMORY.md.",
        proposed_value="- Project anchor: Jarvis and the user are building Jarvis together.",
    )
    _apply_memory_candidate(
        isolated_runtime,
        canonical_key="workspace-memory:stable-context:review-style",
        summary="A bounded stable context may be worth carrying into MEMORY.md.",
        proposed_value="- Stable context: review style still matters across turns.",
    )

    assembly = isolated_runtime.prompt_contract.build_visible_chat_prompt_assembly(
        provider="ollama",
        model="qwen3.5:9b",
        user_message="hvad bygger vi sammen?",
        session_id="test-session",
    )

    assert "MEMORY.md:" in assembly.text
    assert "Project anchor: Jarvis and the user are building Jarvis together." in assembly.text
    assert "Stable context: review style still matters across turns." not in assembly.text


def test_ollama_visible_prompt_can_include_relevant_applied_repo_context_memory(
    isolated_runtime,
) -> None:
    _apply_memory_candidate(
        isolated_runtime,
        canonical_key="workspace-memory:remembered-fact:repo-context",
        summary="A bounded remembered fact may be worth carrying into MEMORY.md.",
        proposed_value="- Working context: the current collaboration is in the Jarvis v2 repo.",
    )
    _apply_memory_candidate(
        isolated_runtime,
        canonical_key="workspace-memory:remembered-fact:project-anchor",
        summary="A bounded remembered fact may be worth carrying into MEMORY.md.",
        proposed_value="- Project anchor: Jarvis and the user are building Jarvis together.",
    )

    assembly = isolated_runtime.prompt_contract.build_visible_chat_prompt_assembly(
        provider="ollama",
        model="qwen3.5:9b",
        user_message="hvilket repo arbejder vi i lige nu?",
        session_id="test-session",
    )

    assert "MEMORY.md:" in assembly.text
    assert "Working context: the current collaboration is in the Jarvis v2 repo." in assembly.text
    assert "Project anchor: Jarvis and the user are building Jarvis together." not in assembly.text


def test_ollama_visible_prompt_does_not_dump_memory_for_irrelevant_generic_query(
    isolated_runtime,
) -> None:
    _apply_memory_candidate(
        isolated_runtime,
        canonical_key="workspace-memory:remembered-fact:project-anchor",
        summary="A bounded remembered fact may be worth carrying into MEMORY.md.",
        proposed_value="- Project anchor: Jarvis and the user are building Jarvis together.",
    )

    assembly = isolated_runtime.prompt_contract.build_visible_chat_prompt_assembly(
        provider="ollama",
        model="qwen3.5:9b",
        user_message="Svar kort på dansk.",
        session_id="test-session",
    )

    assert "MEMORY.md:" not in assembly.text
