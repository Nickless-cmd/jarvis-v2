"""Tests for build_brain_post_web_nudge — encourages remember_this after web tools."""
from __future__ import annotations
import pytest


def test_nudge_returns_text_when_recent_tool_has_urls():
    from core.services.prompt_sections.jarvis_brain_nudge import (
        build_brain_post_web_nudge,
    )
    msgs = [{"role": "tool", "content": "Result: https://example.com/page"}]
    out = build_brain_post_web_nudge(recent_tool_messages=msgs)
    assert "remember_this" in out
    assert "ekstern info" in out


def test_nudge_returns_empty_when_no_url_in_tool_messages():
    from core.services.prompt_sections.jarvis_brain_nudge import (
        build_brain_post_web_nudge,
    )
    msgs = [{"role": "tool", "content": "internal lookup result, no urls"}]
    out = build_brain_post_web_nudge(recent_tool_messages=msgs)
    assert out == ""


def test_nudge_returns_empty_when_no_messages():
    from core.services.prompt_sections.jarvis_brain_nudge import (
        build_brain_post_web_nudge,
    )
    out = build_brain_post_web_nudge(recent_tool_messages=[])
    assert out == ""


def test_nudge_only_inspects_most_recent_message():
    """Older URL-bearing tool result shouldn't trigger if most recent is non-web."""
    from core.services.prompt_sections.jarvis_brain_nudge import (
        build_brain_post_web_nudge,
    )
    msgs = [
        {"role": "tool", "content": "https://old-search.com"},
        {"role": "tool", "content": "internal answer with no urls"},
    ]
    out = build_brain_post_web_nudge(recent_tool_messages=msgs)
    assert out == ""
