from __future__ import annotations

import importlib


def _tools():
    import core.services.chat_flow_preferences as service
    import core.tools.desk_view_tools as tools

    importlib.reload(service)
    return importlib.reload(tools)


def test_tool_schema_has_no_user_identity_escape_hatch(isolated_runtime):
    tools = _tools()
    definition = next(
        item for item in tools.DESK_VIEW_TOOL_DEFINITIONS
        if item["function"]["name"] == "set_chat_flow_preference"
    )

    properties = definition["function"]["parameters"]["properties"]
    assert properties["preference"]["enum"] == ["living", "calm", "adaptive"]
    assert "user_id" not in properties


def test_tool_persists_for_verified_current_user_only(isolated_runtime):
    tools = _tools()
    from core.identity.workspace_context import reset_context, set_context

    first = set_context(workspace_name="a", user_id="user-a", role="member")
    try:
        result = tools.DESK_VIEW_TOOL_HANDLERS["set_chat_flow_preference"](
            {"preference": "calm"}
        )
    finally:
        reset_context(first)

    second = set_context(workspace_name="b", user_id="user-b", role="member")
    try:
        other = tools.DESK_VIEW_TOOL_HANDLERS["set_chat_flow_preference"](
            {"suggestions_enabled": False}
        )
    finally:
        reset_context(second)

    assert result["preference"] == "calm"
    assert result["explicit_user_choice"] is True
    assert other["preference"] == "living"
    assert other["suggestions_enabled"] is False


def test_tool_fails_closed_without_verified_identity(isolated_runtime):
    tools = _tools()
    from core.identity.workspace_context import reset_context, set_context

    token = set_context(workspace_name="bjorn", user_id="claimed-owner", role="")
    try:
        result = tools.DESK_VIEW_TOOL_HANDLERS["set_chat_flow_preference"](
            {"preference": "calm"}
        )
    finally:
        reset_context(token)

    assert result["status"] == "error"
    assert "verified" in result["error"]


def test_tool_rejects_empty_and_invalid_mutations(isolated_runtime):
    tools = _tools()
    from core.identity.workspace_context import reset_context, set_context

    token = set_context(workspace_name="a", user_id="user-a", role="member")
    try:
        empty = tools.DESK_VIEW_TOOL_HANDLERS["set_chat_flow_preference"]({})
        invalid = tools.DESK_VIEW_TOOL_HANDLERS["set_chat_flow_preference"](
            {"preference": "verbose"}
        )
    finally:
        reset_context(token)

    assert empty["status"] == "error"
    assert invalid["status"] == "error"
