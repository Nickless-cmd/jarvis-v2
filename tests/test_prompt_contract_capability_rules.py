"""Tests for visible capability prompt rules."""
from __future__ import annotations

import importlib


def _get_capability_truth_instruction(compact: bool = False) -> str:
    pc = importlib.import_module("apps.api.jarvis_api.services.prompt_contract")
    pc = importlib.reload(pc)
    return pc._visible_capability_truth_instruction(compact=compact) or ""


def test_no_prose_ban_in_capability_rules() -> None:
    """The 'no surrounding prose' rule must be removed."""
    text = _get_capability_truth_instruction()
    assert "no surrounding prose" not in text
    assert "exactly one capability-call line" not in text


def test_prose_allowed_with_capability_tags() -> None:
    """Prompt must allow brief prose alongside capability tags."""
    text = _get_capability_truth_instruction()
    assert "brief sentence" in text or "short" in text.lower()


def test_path_rule_allows_context_inference() -> None:
    """Path rule must allow inferring paths from context, not just user message."""
    text = _get_capability_truth_instruction()
    assert "user message already names one explicit" not in text
    assert "context" in text.lower() or "well-known" in text.lower()


def test_command_rule_allows_inference() -> None:
    """Command rule must allow inferring commands from context."""
    text = _get_capability_truth_instruction()
    assert "already includes one explicit command in backticks" not in text


def test_heartbeat_living_context_line_includes_experimental_prompt_fragments(
    isolated_runtime,
    monkeypatch,
) -> None:
    pc = isolated_runtime.prompt_contract

    body_memory = importlib.import_module("apps.api.jarvis_api.services.body_memory")
    ghost_networks = importlib.import_module(
        "apps.api.jarvis_api.services.ghost_networks"
    )
    parallel_selves = importlib.import_module(
        "apps.api.jarvis_api.services.parallel_selves"
    )
    silence_listener = importlib.import_module(
        "apps.api.jarvis_api.services.silence_listener"
    )
    decision_ghosts = importlib.import_module(
        "apps.api.jarvis_api.services.decision_ghosts"
    )
    memory_tattoos = importlib.import_module(
        "apps.api.jarvis_api.services.memory_tattoos"
    )

    monkeypatch.setattr(body_memory, "format_body_for_prompt", lambda: "body=warm")
    monkeypatch.setattr(
        ghost_networks,
        "format_ghost_for_prompt",
        lambda: "ghosts=audible",
    )
    monkeypatch.setattr(
        parallel_selves,
        "format_self_for_prompt",
        lambda: "selves=aligned",
    )
    monkeypatch.setattr(
        silence_listener,
        "format_silence_for_prompt",
        lambda: "silence=listening",
    )
    monkeypatch.setattr(
        decision_ghosts,
        "format_decision_ghost_for_prompt",
        lambda: "decision_ghosts=present",
    )
    monkeypatch.setattr(
        memory_tattoos,
        "format_tattoo_for_prompt",
        lambda: "tattoos=glowing",
    )

    line = pc._heartbeat_living_context_line()

    assert "body=warm" in line
    assert "ghosts=audible" in line
    assert "selves=aligned" in line
    assert "silence=listening" in line
    assert "decision_ghosts=present" in line
    assert "tattoos=glowing" in line
