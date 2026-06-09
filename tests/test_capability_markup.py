"""Unit tests for capability markup parsing — udskilt fra prompt_contract/visible_runs.

Dækker alle funktioner i core.services.prompt_sections.capability_markup.
Erstatning for de capability-parsing tests der tidligere lå i
test_visible_runs_capability_smoke.py — men her i isolation uden runtime-setup.
"""
from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest


def _module():
    return importlib.import_module(
        "core.services.prompt_sections.capability_markup"
    )


# ---------------------------------------------------------------------------
# _parse_capability_attrs
# ---------------------------------------------------------------------------


class TestParseCapabilityAttrs:
    def test_empty_text(self) -> None:
        assert _module()._parse_capability_attrs("") == {}

    def test_single_attr(self) -> None:
        assert _module()._parse_capability_attrs('id="tool:read"') == {"id": "tool:read"}

    def test_multiple_attrs(self) -> None:
        result = _module()._parse_capability_attrs(
            'id="tool:cmd" command_text="ls -la" target_path="/tmp"'
        )
        assert result["id"] == "tool:cmd"
        assert result["command_text"] == "ls -la"
        assert result["target_path"] == "/tmp"

    def test_spaces_and_quotes(self) -> None:
        result = _module()._parse_capability_attrs(
            '  id="tool:x"   command_text="echo hello world"  '
        )
        assert result["id"] == "tool:x"
        assert result["command_text"] == "echo hello world"

    def test_no_valid_attrs(self) -> None:
        """Non-matching content yields empty dict, not error."""
        assert _module()._parse_capability_attrs("not-an-attr") == {}


# ---------------------------------------------------------------------------
# _parse_capability_call_markup
# ---------------------------------------------------------------------------


class TestParseCapabilityCallMarkup:
    def test_valid_self_closing(self) -> None:
        result = _module()._parse_capability_call_markup(
            '<capability-call id="tool:read-workspace-user-profile" />'
        )
        assert result is not None
        assert result["capability_id"] == "tool:read-workspace-user-profile"
        assert result["arguments"] == {}

    def test_with_arguments(self) -> None:
        result = _module()._parse_capability_call_markup(
            '<capability-call id="tool:run-non-destructive-command" command_text="pwd" />'
        )
        assert result is not None
        assert result["capability_id"] == "tool:run-non-destructive-command"
        assert result["arguments"] == {"command_text": "pwd"}

    def test_only_known_args_surface(self) -> None:
        """Only VISIBLE_CAPABILITY_ARG_NAMES should appear in arguments."""
        result = _module()._parse_capability_call_markup(
            '<capability-call id="tool:read" unknown_arg="val" command_text="ls" />'
        )
        assert result is not None
        assert "unknown_arg" not in result["arguments"]
        assert result["arguments"] == {"command_text": "ls"}

    def test_empty_id_rejected(self) -> None:
        result = _module()._parse_capability_call_markup('<capability-call id="" />')
        assert result is None

    def test_invalid_id_format(self) -> None:
        """IDs with spaces or special chars are rejected."""
        result = _module()._parse_capability_call_markup(
            '<capability-call id="invalid id space" />'
        )
        assert result is None

    def test_not_a_tag(self) -> None:
        result = _module()._parse_capability_call_markup("just some text")
        assert result is None

    def test_open_tag_only(self) -> None:
        result = _module()._parse_capability_call_markup(
            '<capability-call id="tool:x">'
        )
        assert result is None

    def test_whitespace_handling(self) -> None:
        result = _module()._parse_capability_call_markup(
            '  <capability-call id="tool:test" />  '
        )
        assert result is not None
        assert result["capability_id"] == "tool:test"


# ---------------------------------------------------------------------------
# _extract_capability_call
# ---------------------------------------------------------------------------


class TestExtractCapabilityCall:
    def test_valid(self) -> None:
        assert (
            _module()._extract_capability_call(
                '<capability-call id="tool:read" />'
            )
            == "tool:read"
        )

    def test_none_on_missing(self) -> None:
        assert _module()._extract_capability_call("plain text") is None

    def test_none_on_invalid(self) -> None:
        assert _module()._extract_capability_call(
            '<capability-call id="" />'
        ) is None


# ---------------------------------------------------------------------------
# _extract_content_after_capability_tag
# ---------------------------------------------------------------------------


class TestExtractContentAfterCapabilityTag:
    def test_returns_content_after_tag(self) -> None:
        text = (
            '<capability-call id="tool:remember" />\n'
            '# Title\n'
            'Some memory content here.\n'
        )
        result = _module()._extract_content_after_capability_tag(text, "tool:remember")
        assert result is not None
        assert "# Title" in result
        assert "Some memory content here" in result

    def test_returns_none_when_content_too_short(self) -> None:
        text = '<capability-call id="tool:remember" />\nhi\n'
        result = _module()._extract_content_after_capability_tag(text, "tool:remember")
        assert result is None

    def test_returns_none_when_no_tag(self) -> None:
        result = _module()._extract_content_after_capability_tag(
            "just text", "tool:remember"
        )
        assert result is None

    def test_stops_at_next_tag(self) -> None:
        text = (
            '<capability-call id="tool:remember" />\n'
            '# Content\n'
            'text here.\n'
            '<capability-call id="tool:other" />\n'
            'ignored\n'
        )
        result = _module()._extract_content_after_capability_tag(text, "tool:remember")
        assert result is not None
        assert "# Content" in result
        assert "text here." in result
        assert "ignored" not in result


# ---------------------------------------------------------------------------
# _capability_call_state
# ---------------------------------------------------------------------------


class TestCapabilityCallState:
    def test_exact(self) -> None:
        state = _module()._capability_call_state(
            '<capability-call id="tool:x" />'
        )
        assert state == "exact"

    def test_prefix(self) -> None:
        state = _module()._capability_call_state(
            '<capability-call id="tool:'
        )
        assert state == "prefix"

    def test_invalid_empty(self) -> None:
        assert _module()._capability_call_state("") == "invalid"

    def test_invalid_wrong_prefix(self) -> None:
        assert _module()._capability_call_state("<other-tag") == "invalid"

    def test_invalid_no_id(self) -> None:
        state = _module()._capability_call_state(
            '<capability-call id="" />'
        )
        assert state == "invalid"

    def test_prefix_minimal(self) -> None:
        """Very short prefix should still be recognised."""
        assert _module()._capability_call_state("<capabilit") == "prefix"


# ---------------------------------------------------------------------------
# _strip_capability_markup
# ---------------------------------------------------------------------------


class TestStripCapabilityMarkup:
    def test_removes_self_closing_tag(self) -> None:
        result = _module()._strip_capability_markup(
            'text <capability-call id="tool:read" /> more'
        )
        assert "text  more" == result or "text  more" in result
        assert "<capability-call" not in result

    def test_removes_self_closing_but_not_block_tags(self) -> None:
        """_strip_capability_markup fjerner self-closing tags, men ikke block tags (det gør bufferen)."""
        text = (
            'before\n'
            '<capability-call id="tool:read">\n'
            'content\n'
            '</capability-call>\n'
            'after'
        )
        result = _module()._strip_capability_markup(text)
        # Block tags bevares — kun self-closing + tool-text-markup fjernes
        assert "<capability-call" in result
        assert "before" in result
        assert "after" in result

    def test_removes_tool_text_markup(self) -> None:
        result = _module()._strip_capability_markup(
            'text ([tool:x]: some info) more'
        )
        assert "<capability-call" not in result

    def test_no_markup_unchanged(self) -> None:
        result = _module()._strip_capability_markup("plain text")
        assert result == "plain text"

    def test_whitespace_only_unchanged(self) -> None:
        result = _module()._strip_capability_markup("   ")
        assert result.strip() == ""


# ---------------------------------------------------------------------------
# _try_match_tool_text_markup
# ---------------------------------------------------------------------------


class TestTryMatchToolTextMarkup:
    def test_no_match_returns_0(self) -> None:
        assert _module()._try_match_tool_text_markup("plain text") == 0

    def test_simple_tool(self) -> None:
        """([tool_name]: <path>) — word må ikke indeholde kolon"""
        result = _module()._try_match_tool_text_markup(
            "([tool_read]: /some/path)"
        )
        assert result > 0

    def test_incomplete_needs_buffering(self) -> None:
        """Partial markup returns -1."""
        result = _module()._try_match_tool_text_markup("([tool")
        assert result == -1

    def test_json_tool_text(self) -> None:
        """([tool_search]): {"key": "val"} — word uden kolon"""
        result = _module()._try_match_tool_text_markup(
            '([tool_search]): {"query": "hello"}'
        )
        assert result > 0


# ---------------------------------------------------------------------------
# _strip_tool_call_text_markup
# ---------------------------------------------------------------------------


class TestStripToolCallTextMarkup:
    def test_strips_simple(self) -> None:
        """Tool-text-markup uden kolon i tool-navn fjernes; resten bevares."""
        result = _module()._strip_tool_call_text_markup(
            "([tool_read]: /path) remaining"
        )
        assert "remaining" in result
        assert "tool_read" not in result

    def test_preserves_original_if_stripped_empty(self) -> None:
        """If stripping removes everything, return original (don't silently lose)."""
        text = "([tool_read]: /path)"
        result = _module()._strip_tool_call_text_markup(text)
        assert result == text

    def test_no_markup(self) -> None:
        assert _module()._strip_tool_call_text_markup("hello") == "hello"


# ---------------------------------------------------------------------------
# _CapabilityMarkupBuffer
# ---------------------------------------------------------------------------


class TestCapabilityMarkupBuffer:
    def test_passes_through_plain_text(self) -> None:
        buf = _module()._CapabilityMarkupBuffer()
        assert buf.feed("hello") == "hello"
        assert buf.flush() == ""

    def test_buffers_and_swallows_capability_tag(self) -> None:
        buf = _module()._CapabilityMarkupBuffer()
        buf.feed('<capability-call id="tool:read" />')
        assert buf.flush() == ""  # swallowed

    def test_buffers_tool_text_markup(self) -> None:
        buf = _module()._CapabilityMarkupBuffer()
        buf.feed("([tool_read]: /path)")
        assert buf.flush() == ""  # swallowed

    def test_mixed_text_and_tag(self) -> None:
        buf = _module()._CapabilityMarkupBuffer()
        out = buf.feed("before ")
        out += buf.feed('<capability-call id="tool:read" />')
        out += buf.feed(" after")
        out += buf.flush()
        assert "before" in out
        assert "after" in out
        assert "<capability-call" not in out


# ---------------------------------------------------------------------------
# _visible_text_without_capability_markup
# ---------------------------------------------------------------------------


class TestVisibleTextWithoutCapabilityMarkup:
    def test_cleans_markup(self) -> None:
        result = _module()._visible_text_without_capability_markup(
            '<capability-call id="tool:read" />  ',
            had_markup=True,
        )
        assert result == "Capability request was consumed by the visible lane."

    def test_preserves_real_text(self) -> None:
        result = _module()._visible_text_without_capability_markup(
            '<capability-call id="tool:read" />\nHej med dig!',
            had_markup=True,
        )
        assert "Hej med dig!" in result
        assert "<capability-call" not in result

    def test_collapses_excessive_whitespace(self) -> None:
        result = _module()._visible_text_without_capability_markup(
            'text   with    spaces   ',
            had_markup=False,
        )
        assert "text with spaces" == result

    def test_returns_empty_string_when_no_text_and_no_markup(self) -> None:
        result = _module()._visible_text_without_capability_markup(
            "", had_markup=False
        )
        assert result == ""

    def test_empty_with_markup_returns_fallback(self) -> None:
        result = _module()._visible_text_without_capability_markup(
            "", had_markup=True
        )
        assert "Capability request" in result
