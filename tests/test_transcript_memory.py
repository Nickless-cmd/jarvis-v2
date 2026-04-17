"""Tests for transcript memory pipeline fixes.

Covers: structured transcript messages, tool compression, "Done." fix,
raised limits, and session continuity improvements.
"""
from __future__ import annotations
import pytest


# ── Structured transcript builder ─────────────────────────────────────

def test_structured_transcript_empty_session() -> None:
    """Returns empty list for missing session."""
    from core.services.prompt_contract import (
        _build_structured_transcript_messages,
    )
    result = _build_structured_transcript_messages(None, limit=20, include=True)
    assert result == []


def test_structured_transcript_disabled() -> None:
    """Returns empty list when include=False."""
    from core.services.prompt_contract import (
        _build_structured_transcript_messages,
    )
    result = _build_structured_transcript_messages("some-session", limit=20, include=False)
    assert result == []


def test_structured_transcript_user_assistant_roles() -> None:
    """User and assistant messages get correct roles."""
    import unittest.mock as mock
    from core.services.prompt_contract import (
        _build_structured_transcript_messages,
    )
    fake_history = [
        {"role": "user", "content": "Hej Jarvis", "created_at": "2026-01-01T00:00:00"},
        {"role": "assistant", "content": "Hej! Hvad kan jeg hjælpe med?", "created_at": "2026-01-01T00:00:01"},
    ]
    with mock.patch(
        "core.services.prompt_contract.recent_chat_session_messages",
        return_value=fake_history,
    ):
        result = _build_structured_transcript_messages("test-session", limit=20, include=True)
    assert len(result) == 2
    assert result[0]["role"] == "user"
    assert result[0]["content"] == "Hej Jarvis"
    assert result[1]["role"] == "assistant"
    assert "Hvad kan jeg hjælpe med?" in result[1]["content"]


def test_structured_transcript_tool_compressed_into_assistant() -> None:
    """Tool messages are merged into preceding assistant message as annotation."""
    import unittest.mock as mock
    from core.services.prompt_contract import (
        _build_structured_transcript_messages,
    )
    fake_history = [
        {"role": "user", "content": "Hvad er klokken?", "created_at": "2026-01-01T00:00:00"},
        {"role": "assistant", "content": "Lad mig tjekke.", "created_at": "2026-01-01T00:00:01"},
        {"role": "tool", "content": "[get_time]: 14:30", "created_at": "2026-01-01T00:00:02"},
        {"role": "assistant", "content": "Klokken er 14:30.", "created_at": "2026-01-01T00:00:03"},
    ]
    with mock.patch(
        "core.services.prompt_contract.recent_chat_session_messages",
        return_value=fake_history,
    ):
        result = _build_structured_transcript_messages("test-session", limit=20, include=True)

    # Tool should be compressed into the first assistant message
    roles = [m["role"] for m in result]
    assert "tool" not in roles, "Tool messages should not appear as separate turns"

    # The tool result should be annotated on the preceding assistant message
    first_assistant = next(m for m in result if m["role"] == "assistant")
    assert "[get_time]" in first_assistant["content"]


def test_structured_transcript_tool_without_preceding_assistant() -> None:
    """Tool message without preceding assistant creates synthetic annotation."""
    import unittest.mock as mock
    from core.services.prompt_contract import (
        _build_structured_transcript_messages,
    )
    fake_history = [
        {"role": "user", "content": "Gør noget", "created_at": "2026-01-01T00:00:00"},
        {"role": "tool", "content": "[bash]: output here", "created_at": "2026-01-01T00:00:01"},
    ]
    with mock.patch(
        "core.services.prompt_contract.recent_chat_session_messages",
        return_value=fake_history,
    ):
        result = _build_structured_transcript_messages("test-session", limit=20, include=True)

    roles = [m["role"] for m in result]
    assert "tool" not in roles


def test_structured_transcript_truncation() -> None:
    """Long messages are truncated at 1600 chars."""
    import unittest.mock as mock
    from core.services.prompt_contract import (
        _build_structured_transcript_messages,
    )
    long_content = "x" * 3000
    fake_history = [
        {"role": "user", "content": long_content, "created_at": "2026-01-01T00:00:00"},
    ]
    with mock.patch(
        "core.services.prompt_contract.recent_chat_session_messages",
        return_value=fake_history,
    ):
        result = _build_structured_transcript_messages("test-session", limit=20, include=True)

    assert len(result) == 1
    assert len(result[0]["content"]) <= 1600


def test_structured_transcript_no_tool_slot_waste() -> None:
    """3 tool calls + 1 user + 1 assistant should produce 2-3 messages, not 5."""
    import unittest.mock as mock
    from core.services.prompt_contract import (
        _build_structured_transcript_messages,
    )
    fake_history = [
        {"role": "user", "content": "Do three things", "created_at": "2026-01-01T00:00:00"},
        {"role": "assistant", "content": "Working on it.", "created_at": "2026-01-01T00:00:01"},
        {"role": "tool", "content": "[read_file]: file content", "created_at": "2026-01-01T00:00:02"},
        {"role": "tool", "content": "[search]: found 5 results", "created_at": "2026-01-01T00:00:03"},
        {"role": "tool", "content": "[bash]: ok", "created_at": "2026-01-01T00:00:04"},
        {"role": "assistant", "content": "All done.", "created_at": "2026-01-01T00:00:05"},
    ]
    with mock.patch(
        "core.services.prompt_contract.recent_chat_session_messages",
        return_value=fake_history,
    ):
        result = _build_structured_transcript_messages("test-session", limit=20, include=True)

    # Should be 3 messages max (user, assistant+tool annotations, assistant)
    assert len(result) <= 4, f"Expected ≤4 messages but got {len(result)}: {[m['role'] for m in result]}"
    roles = [m["role"] for m in result]
    assert "tool" not in roles


# ── PromptAssembly structured transcript field ────────────────────────

def test_prompt_assembly_has_transcript_messages_field() -> None:
    """PromptAssembly dataclass should have transcript_messages field."""
    from core.services.prompt_contract import PromptAssembly
    assembly = PromptAssembly(
        mode="test",
        text="test",
        included_files=[],
        conditional_files=[],
        derived_inputs=[],
        excluded_files=[],
        transcript_messages=[{"role": "user", "content": "test"}],
    )
    assert assembly.transcript_messages is not None
    assert len(assembly.transcript_messages) == 1


def test_prompt_assembly_transcript_messages_default_none() -> None:
    """transcript_messages defaults to None."""
    from core.services.prompt_contract import PromptAssembly
    assembly = PromptAssembly(
        mode="test",
        text="test",
        included_files=[],
        conditional_files=[],
        derived_inputs=[],
        excluded_files=[],
    )
    assert assembly.transcript_messages is None


# ── "Done." fix ───────────────────────────────────────────────────────

def test_done_replacement_not_in_visible_runs() -> None:
    """visible_runs.py should no longer contain bare 'Done.' fallback."""
    from pathlib import Path
    source = Path("apps/api/jarvis_api/services/visible_runs.py").read_text()
    # Check that the old "Done." pattern is gone
    assert 'followup_text = "Done."' not in source, \
        "bare 'Done.' fallback should be replaced with meaningful summary"
    # Check that [Completed: ...] pattern exists
    assert "[Completed:" in source or "[Completed]" in source, \
        "should use [Completed: tool_names] pattern"


# ── Limits ────────────────────────────────────────────────────────────

def test_transcript_limit_raised_above_20() -> None:
    """Compact transcript limit should be > 20 (was 20, now 50)."""
    from pathlib import Path
    source = Path("apps/api/jarvis_api/services/prompt_contract.py").read_text()
    # Should contain limit=50 for compact (not 20)
    assert "limit=50" in source, "Compact transcript limit should be raised to 50"
