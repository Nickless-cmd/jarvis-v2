from core.tools.simple_tools import _TOOL_HANDLERS, TOOL_DEFINITIONS


def test_dispatch_tool_registered():
    assert "dispatch_to_claude_code" in _TOOL_HANDLERS
    assert "dispatch_status" in _TOOL_HANDLERS
    assert "dispatch_cancel" in _TOOL_HANDLERS


def test_dispatch_tool_definition_exists():
    names = {d.get("name") for d in TOOL_DEFINITIONS}
    assert "dispatch_to_claude_code" in names
    assert "dispatch_status" in names
    assert "dispatch_cancel" in names
