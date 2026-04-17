"""Unit tests for approval-feedback pattern detection in inner voice."""

from __future__ import annotations

from core.services import inner_voice_daemon


def test_returns_none_with_few_events(monkeypatch) -> None:
    monkeypatch.setattr(
        inner_voice_daemon,
        "list_approval_feedback",
        lambda limit=10: [
            {"approval_state": "approved", "tool_name": "repo"},
        ],
    )

    assert inner_voice_daemon._recent_approval_sentiment_summary() is None


def test_detects_denial_streak(monkeypatch) -> None:
    monkeypatch.setattr(
        inner_voice_daemon,
        "list_approval_feedback",
        lambda limit=10: [
            {"approval_state": "denied", "tool_name": "shell"},
            {"approval_state": "denied", "tool_name": "mail"},
            {"approval_state": "denied", "tool_name": "shell"},
            {"approval_state": "approved", "tool_name": "repo"},
        ],
    )

    summary = inner_voice_daemon._recent_approval_sentiment_summary()

    assert summary is not None
    assert summary["pattern"] == "recent_denials"
    assert summary["count"] == 3
    assert summary["tools"] == ["shell", "mail"]


def test_detects_approval_streak(monkeypatch) -> None:
    monkeypatch.setattr(
        inner_voice_daemon,
        "list_approval_feedback",
        lambda limit=10: [
            {"approval_state": "approved", "tool_name": "shell"},
            {"approval_state": "approved", "tool_name": "mail"},
            {"approval_state": "approved", "tool_name": "shell"},
            {"approval_state": "approved", "tool_name": "notes"},
            {"approval_state": "approved", "tool_name": "repo"},
            {"approval_state": "denied", "tool_name": "browser"},
        ],
    )

    summary = inner_voice_daemon._recent_approval_sentiment_summary()

    assert summary is not None
    assert summary["pattern"] == "approval_streak"
    assert summary["count"] == 5
    assert summary["tools"] == ["shell", "mail", "notes"]
