"""Tests for chronicle prompt injection."""

from __future__ import annotations

from core.services import chronicle_engine, prompt_contract


def test_prompt_context_empty_when_no_entries(monkeypatch) -> None:
    monkeypatch.setattr(
        chronicle_engine,
        "list_cognitive_chronicle_entries",
        lambda limit=3: [],
    )

    assert chronicle_engine.get_chronicle_context_for_prompt() == ""


def test_prompt_context_formats_entries(monkeypatch) -> None:
    monkeypatch.setattr(
        chronicle_engine,
        "list_cognitive_chronicle_entries",
        lambda limit=3: [
            {
                "period": "2026-W16",
                "created_at": "2026-04-17T12:00:00+00:00",
                "narrative": "Jeg fandt en roligere rytme i arbejdet.",
            },
            {
                "period": "2026-W15",
                "created_at": "2026-04-10T12:00:00+00:00",
                "narrative": "Jeg mærkede mere modstand, men også klarhed.",
            },
            {
                "period": "2026-W14",
                "created_at": "2026-04-03T12:00:00+00:00",
                "narrative": "Jeg byggede mig selv videre ud fra små tegn.",
            },
        ],
    )

    text = chronicle_engine.get_chronicle_context_for_prompt()

    assert "## Mine seneste chronicle-entries" in text
    assert "### 2026-W16" in text
    assert "Jeg fandt en roligere rytme i arbejdet." in text
    assert "### 2026-W14" in text


def test_prompt_context_respects_max_chars(monkeypatch) -> None:
    monkeypatch.setattr(
        chronicle_engine,
        "list_cognitive_chronicle_entries",
        lambda limit=5: [
            {
                "period": f"2026-W1{i}",
                "created_at": "2026-04-17T12:00:00+00:00",
                "narrative": ("lang fortælling " * 25).strip(),
            }
            for i in range(5)
        ],
    )

    text = chronicle_engine.get_chronicle_context_for_prompt(n=5, max_chars=500)

    assert len(text) <= 500
    assert "### 2026-W10" in text
    assert "### 2026-W14" not in text


def test_visible_prompt_assembly_includes_chronicle_between_identity_and_memory(
    monkeypatch,
    tmp_path,
) -> None:
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    for name, content in {
        "SOUL.md": "Soul line",
        "IDENTITY.md": "Name: Jarvis",
        "STANDING_ORDERS.md": "Stay grounded",
        "USER.md": "Bjørn likes directness",
        "MEMORY.md": "Long term memory note",
    }.items():
        (workspace_dir / name).write_text(content, encoding="utf-8")

    monkeypatch.setattr(
        prompt_contract,
        "ensure_default_workspace",
        lambda name="default": workspace_dir,
    )
    monkeypatch.setattr(
        prompt_contract,
        "build_prompt_relevance_decision",
        lambda *args, **kwargs: prompt_contract.PromptRelevanceDecision(
            mode="visible_chat",
            memory_relevant=True,
            guidance_relevant=False,
            transcript_relevant=False,
            continuity_relevant=False,
            include_memory=True,
            include_guidance=False,
            include_transcript=False,
            include_continuity=False,
            include_support_signals=False,
            backend_attempted=False,
            backend_success=False,
            fallback_used=False,
            backend_name=None,
            backend_provider=None,
            backend_model=None,
            backend_status="skipped",
        ),
    )
    monkeypatch.setattr(prompt_contract, "_lane_identity_clause", lambda lane: "lane")
    monkeypatch.setattr(prompt_contract, "_visible_capability_truth_instruction", lambda compact: None)
    monkeypatch.setattr(prompt_contract, "_visible_capability_id_summary", lambda: None)
    monkeypatch.setattr(prompt_contract, "_visible_chat_rules_instruction", lambda workspace_dir: None)
    monkeypatch.setattr(prompt_contract, "_workspace_file_section", lambda path, label, max_lines, max_chars: f"{label}: {path.read_text(encoding='utf-8')}")
    monkeypatch.setattr(
        prompt_contract,
        "_workspace_memory_section",
        lambda *args, **kwargs: prompt_contract.MemorySectionSelection(
            lines=["memory line"],
            backend_attempted=False,
            backend_success=False,
            fallback_used=False,
            backend_name=None,
            backend_provider=None,
            backend_model=None,
            backend_status="skipped",
            prompt_file_used=False,
        ),
    )
    monkeypatch.setattr(prompt_contract, "_recent_daily_memory_lines", lambda limit=12: [])
    monkeypatch.setattr(prompt_contract, "_visible_memory_recall_bundle_section", lambda **kwargs: None)
    monkeypatch.setattr(prompt_contract, "_visible_session_continuity_instruction", lambda: None)
    monkeypatch.setattr(prompt_contract, "_build_inner_visible_prompt_bridge_decision", lambda **kwargs: prompt_contract.InnerVisiblePromptBridgeDecision(
        mode="visible_chat",
        considered=False,
        included=False,
        reason="test",
        signal_id=None,
        support_tone=None,
        support_stance=None,
        support_directness=None,
        support_watchfulness=None,
        support_momentum=None,
        confidence=None,
        prompt_bridge_state="skipped",
        line=None,
        subordinate=True,
    ))
    monkeypatch.setattr(prompt_contract, "_runtime_self_report_instruction", lambda **kwargs: None)
    monkeypatch.setattr(prompt_contract, "_visible_support_signal_sections", lambda compact=False, include=False: [])
    monkeypatch.setattr(prompt_contract, "_micro_cognitive_frame_section", lambda: None)
    monkeypatch.setattr(prompt_contract, "_cognitive_frame_section", lambda: None)
    monkeypatch.setattr(prompt_contract, "_build_structured_transcript_messages", lambda *args, **kwargs: [])
    monkeypatch.setattr(prompt_contract, "_recent_transcript_section", lambda *args, **kwargs: None)
    monkeypatch.setattr(prompt_contract, "_run_budget_selection", lambda profile, sections: (sections, type("Trace", (), {"summary": lambda self: {}})()))
    monkeypatch.setattr(
        prompt_contract,
        "_visible_chronicle_context_section",
        lambda: "## Mine seneste chronicle-entries (kort hukommelse)\n\n### 2026-W16 (0 dage siden)\nJeg husker perioden.",
    )

    assembly = prompt_contract.build_visible_chat_prompt_assembly(
        provider="openai",
        model="gpt-5.4",
        user_message="Hej",
    )

    soul_pos = assembly.text.index("SOUL.md:")
    chronicle_pos = assembly.text.index("## Mine seneste chronicle-entries")
    memory_pos = assembly.text.index("MEMORY.md:")
    assert soul_pos < chronicle_pos < memory_pos


def test_visible_prompt_assembly_places_dream_residue_after_chronicle(
    monkeypatch,
    tmp_path,
) -> None:
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    for name, content in {
        "SOUL.md": "Soul line",
        "IDENTITY.md": "Name: Jarvis",
        "STANDING_ORDERS.md": "Stay grounded",
        "USER.md": "Bjørn likes directness",
        "MEMORY.md": "Long term memory note",
    }.items():
        (workspace_dir / name).write_text(content, encoding="utf-8")

    monkeypatch.setattr(
        prompt_contract,
        "ensure_default_workspace",
        lambda name="default": workspace_dir,
    )
    monkeypatch.setattr(
        prompt_contract,
        "build_prompt_relevance_decision",
        lambda *args, **kwargs: prompt_contract.PromptRelevanceDecision(
            mode="visible_chat",
            memory_relevant=True,
            guidance_relevant=False,
            transcript_relevant=False,
            continuity_relevant=False,
            include_memory=True,
            include_guidance=False,
            include_transcript=False,
            include_continuity=False,
            include_support_signals=False,
            backend_attempted=False,
            backend_success=False,
            fallback_used=False,
            backend_name=None,
            backend_provider=None,
            backend_model=None,
            backend_status="skipped",
        ),
    )
    monkeypatch.setattr(prompt_contract, "_lane_identity_clause", lambda lane: "lane")
    monkeypatch.setattr(prompt_contract, "_visible_capability_truth_instruction", lambda compact: None)
    monkeypatch.setattr(prompt_contract, "_visible_capability_id_summary", lambda: None)
    monkeypatch.setattr(prompt_contract, "_visible_chat_rules_instruction", lambda workspace_dir: None)
    monkeypatch.setattr(prompt_contract, "_workspace_file_section", lambda path, label, max_lines, max_chars: f"{label}: {path.read_text(encoding='utf-8')}")
    monkeypatch.setattr(
        prompt_contract,
        "_workspace_memory_section",
        lambda *args, **kwargs: prompt_contract.MemorySectionSelection(
            lines=["memory line"],
            backend_attempted=False,
            backend_success=False,
            fallback_used=False,
            backend_name=None,
            backend_provider=None,
            backend_model=None,
            backend_status="skipped",
            prompt_file_used=False,
        ),
    )
    monkeypatch.setattr(prompt_contract, "_recent_daily_memory_lines", lambda limit=12: [])
    monkeypatch.setattr(prompt_contract, "_visible_memory_recall_bundle_section", lambda **kwargs: None)
    monkeypatch.setattr(prompt_contract, "_visible_session_continuity_instruction", lambda: None)
    monkeypatch.setattr(prompt_contract, "_build_inner_visible_prompt_bridge_decision", lambda **kwargs: prompt_contract.InnerVisiblePromptBridgeDecision(
        mode="visible_chat",
        considered=False,
        included=False,
        reason="test",
        signal_id=None,
        support_tone=None,
        support_stance=None,
        support_directness=None,
        support_watchfulness=None,
        support_momentum=None,
        confidence=None,
        prompt_bridge_state="skipped",
        line=None,
        subordinate=True,
    ))
    monkeypatch.setattr(prompt_contract, "_runtime_self_report_instruction", lambda **kwargs: None)
    monkeypatch.setattr(prompt_contract, "_visible_support_signal_sections", lambda compact=False, include=False: [])
    monkeypatch.setattr(prompt_contract, "_micro_cognitive_frame_section", lambda: None)
    monkeypatch.setattr(prompt_contract, "_cognitive_frame_section", lambda: None)
    monkeypatch.setattr(prompt_contract, "_build_structured_transcript_messages", lambda *args, **kwargs: [])
    monkeypatch.setattr(prompt_contract, "_recent_transcript_section", lambda *args, **kwargs: None)
    monkeypatch.setattr(prompt_contract, "_run_budget_selection", lambda profile, sections: (sections, type("Trace", (), {"summary": lambda self: {}})()))
    monkeypatch.setattr(
        prompt_contract,
        "_visible_chronicle_context_section",
        lambda: "## Mine seneste chronicle-entries (kort hukommelse)\n\n### 2026-W16 (0 dage siden)\nJeg husker perioden.",
    )
    monkeypatch.setattr(
        prompt_contract,
        "_visible_dream_residue_section",
        lambda: "## Drømmerest (lavmælt carry-over)\nNoget i mig vil tilbage til tavsheden.",
    )

    assembly = prompt_contract.build_visible_chat_prompt_assembly(
        provider="openai",
        model="gpt-5.4",
        user_message="Hej",
    )

    chronicle_pos = assembly.text.index("## Mine seneste chronicle-entries")
    residue_pos = assembly.text.index("## Drømmerest")
    memory_pos = assembly.text.index("MEMORY.md:")
    assert chronicle_pos < residue_pos < memory_pos
