"""Tests for core.tools.tool_scoping — rolle/scope allowlist-logik."""
from __future__ import annotations

from core.tools.tool_scoping import (
    allowed_tool_names,
    filter_tool_definitions,
    tool_scope,
    current_tool_scope,
    CHAT_MODE_TOOLS_BASE,
    CHAT_MODE_OWNER_EXTRA,
    OWNER_ONLY_TOOLS,
)

# Et repræsentativt udsnit af tool-navne på tværs af kategorier.
ALL = [
    "web_search", "analyze_image", "remember_this", "read_mood",
    "search_jarvis_brain", "read_file", "search", "find_files",
    "bash", "write_file", "operator_bash", "dispatch_to_claude_code",
    "schedule_recurring", "get_weather",
]


class TestChatScope:

    def test_owner_chat_gets_base_plus_file_reads(self):
        allow = allowed_tool_names(role="owner", scope="chat", all_names=ALL)
        assert "web_search" in allow
        assert "remember_this" in allow
        assert "read_file" in allow and "search" in allow and "find_files" in allow
        # owner beholder owner-only der er i allowlisten
        assert "search_jarvis_brain" in allow

    def test_member_chat_no_file_reads_no_owner_only(self):
        allow = allowed_tool_names(role="member", scope="chat", all_names=ALL)
        assert "web_search" in allow
        assert "remember_this" in allow       # hukommelse-write tilladt
        assert "read_file" not in allow        # ingen fil-læsning for member
        assert "search" not in allow
        assert "search_jarvis_brain" not in allow  # owner-only strippet

    def test_chat_blocks_actions_for_all(self):
        for role in ("owner", "member", ""):
            allow = allowed_tool_names(role=role, scope="chat", all_names=ALL)
            assert "bash" not in allow
            assert "write_file" not in allow
            assert "operator_bash" not in allow
            assert "dispatch_to_claude_code" not in allow
            assert "schedule_recurring" not in allow

    def test_empty_role_treated_as_owner_in_chat(self):
        allow = allowed_tool_names(role="", scope="chat", all_names=ALL)
        assert "read_file" in allow  # unbound legacy → owner-agtig


class TestNonChatScope:

    def test_owner_unrestricted(self):
        allow = allowed_tool_names(role="owner", scope="", all_names=ALL)
        assert allow == set(ALL)

    def test_member_strips_owner_only(self):
        allow = allowed_tool_names(role="member", scope="", all_names=ALL)
        assert "bash" not in allow
        assert "write_file" not in allow
        assert "search_jarvis_brain" not in allow
        assert "web_search" in allow
        assert "read_file" in allow  # ikke owner-only


class TestFilterDefinitions:

    def test_filters_definitions_by_name(self):
        defs = [
            {"function": {"name": "web_search"}},
            {"function": {"name": "bash"}},
            {"function": {"name": "read_file"}},
        ]
        out = filter_tool_definitions(defs, role="member", scope="chat")
        names = {d["function"]["name"] for d in out}
        assert names == {"web_search"}  # bash owner-only, read_file owner-extra


class TestScopeContextVar:

    def test_context_manager_sets_and_resets(self):
        assert current_tool_scope() == ""
        with tool_scope("chat"):
            assert current_tool_scope() == "chat"
        assert current_tool_scope() == ""


class TestAllowlistSanity:

    def test_base_and_owner_extra_disjoint(self):
        assert not (CHAT_MODE_TOOLS_BASE & CHAT_MODE_OWNER_EXTRA)

    def test_owner_extra_are_read_only_files(self):
        assert CHAT_MODE_OWNER_EXTRA == {"read_file", "search", "find_files"}

    def test_no_action_tools_in_base(self):
        for t in ("bash", "write_file", "edit_file", "operator_bash", "schedule_recurring"):
            assert t not in CHAT_MODE_TOOLS_BASE
