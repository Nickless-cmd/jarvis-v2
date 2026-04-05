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
