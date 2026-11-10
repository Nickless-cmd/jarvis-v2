from core.tools.tool_scoping import RETIRED_AGENT_CREATION_TOOLS, is_tool_allowed


def test_relay_to_agent_is_in_retired_list():
    assert "relay_to_agent" in RETIRED_AGENT_CREATION_TOOLS


def test_relay_to_agent_is_blocked_even_for_owner():
    assert is_tool_allowed(role="owner", scope="", name="relay_to_agent") is False
