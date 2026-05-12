from __future__ import annotations

import sys
import types


def test_heartbeat_self_knowledge_renders_grounded_foreground_entry(monkeypatch):
    from core.services import prompt_heartbeat_self_knowledge as heartbeat

    fake_runtime_self_knowledge = types.SimpleNamespace(
        build_self_knowledge_prompt_section=lambda: (
            "Self-knowledge:\n"
            "- source=runtime_self_model | confidence=bounded"
        )
    )
    monkeypatch.setitem(
        sys.modules,
        "core.services.runtime_self_knowledge",
        fake_runtime_self_knowledge,
    )

    section = heartbeat.build_heartbeat_self_knowledge_section()

    assert section is not None
    assert "Foreground runtime truths:" in section
    assert "source=runtime_self_model" in section


def test_prompt_support_world_model_signal_is_subordinate(monkeypatch):
    from core.services import prompt_support_signals as signals

    monkeypatch.setattr(
        signals,
        "list_runtime_world_model_signals",
        lambda limit=8: [
            {
                "status": "active",
                "confidence": "high",
                "title": "Prediction calibration",
                "signal_type": "workspace-scope-assumption",
            }
        ],
    )

    section = signals._world_model_support_signal_instruction()

    assert section is not None
    assert "World-model support signal:" in section
    assert "dominant_world_thread=Prediction calibration" in section
    assert "Use only as subordinate support" in section


def test_continuity_wake_block_reports_capsule_without_performing_identity():
    from core.services import continuity

    block = continuity.build_wake_up_block(
        {
            "wake_provenance": {"hours_since_last_session": 2.0},
            "mood": {"curiosity": 0.7, "confidence": 0.6, "bearing": "neutral"},
            "attention": {"current_focus": "partial triage"},
            "relation": {"relationship_phase": "co-development"},
            "somatic": {},
            "goals": {},
            "recent_activity": {},
        }
    )

    assert block is not None
    assert "CONTINUITY" in block
    assert "Focus: partial triage" in block
    assert "Continuity is reconstructed from stored capsule data." in block
    assert "I don't fake continuity" not in block


def test_development_sense_resistance_language_stays_descriptive(monkeypatch):
    from core.services import development_sense

    monkeypatch.setattr(
        development_sense,
        "growth_pulse",
        lambda: {"score": 0.3, "label": "næsten stillestående"},
    )
    monkeypatch.setattr(development_sense, "stuck_signal", lambda: None)
    monkeypatch.setattr(development_sense, "appetite_signal", lambda: None)
    monkeypatch.setattr(
        development_sense,
        "resistance_signal",
        lambda: {
            "flags": ["agency drift z=-2.3 | baseline-afvigelse over tærskel"]
        },
    )

    section = development_sense.development_sense_section()

    assert section is not None
    assert "baseline-afvigelse over tærskel" in section
    assert "du flytter" not in section
    assert "du holder" not in section


def test_experience_episode_prompt_helpers_are_bounded_and_structured():
    from core.services import experience_episodes

    context = experience_episodes.build_context_text(
        intent="kortlæg PARTIAL services",
        active_loops=["capability audit", "theater cleanup"],
        last_tools=["rg", "pytest"],
        session_phase="triage",
    )

    assert "intent: kortlæg PARTIAL services" in context
    assert "active_loops: capability audit, theater cleanup" in context
    assert "last_tools: rg, pytest" in context

    rendered = experience_episodes.format_episode_for_prompt(
        {
            "similarity": 0.8123,
            "age_minutes": 90,
            "session_phase": "triage",
            "tool_sequence": ["rg", "sed", "pytest", "ruff", "audit"],
            "outcome_signals": {"tick_quality": 0.8, "tool_errors": 0},
            "user_corrected": False,
        },
        max_chars=90,
    )

    assert rendered.startswith("sim=0.81 (1h ago, triage): tools=[rg, sed, pytest, ruff")
    assert len(rendered) <= 90
