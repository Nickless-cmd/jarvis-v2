"""Tests for append_chat_message content_json parameter."""
from __future__ import annotations

import json

import pytest


@pytest.fixture()
def isolated_runtime():
    """Fixture for isolated runtime (from conftest)."""
    pass


def _sid():
    """Helper to create a new session and return its ID."""
    from core.services.chat_sessions import create_chat_session
    return create_chat_session(title="t")["id"]


def test_append_persists_content_json_when_given():
    """append_chat_message stores content_json when provided."""
    sid = _sid()
    blocks = [
        {"type": "text", "text": "svar"},
        {"type": "tool_use", "id": "toolu_1", "name": "bash", "input": {}},
    ]
    result = append_chat_message(
        session_id=sid,
        role="assistant",
        content="svar",
        content_json=json.dumps(blocks),
    )
    assert result["content_json"] == json.dumps(blocks)


def test_append_without_content_json_returns_none():
    """append_chat_message returns None for content_json when not provided."""
    sid = _sid()
    result = append_chat_message(
        session_id=sid, role="assistant", content="ren tekst"
    )
    assert result.get("content_json") is None


# Import at end to avoid circular imports at module level
from core.services.chat_sessions import append_chat_message  # noqa: E402, F401
