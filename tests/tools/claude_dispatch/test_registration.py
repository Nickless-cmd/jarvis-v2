from core.tools.simple_tools import _TOOL_HANDLERS, TOOL_DEFINITIONS


def test_dispatch_tool_registered():
    assert "dispatch_to_claude_code" in _TOOL_HANDLERS
    assert "dispatch_status" in _TOOL_HANDLERS
    assert "dispatch_cancel" in _TOOL_HANDLERS


def test_dispatch_tool_definition_exists():
    """Navnet ligger under `function` — ikke i roden.

    Denne test laeste `d["name"]` og var groen, fordi definitionerne LAA i
    Anthropic-form midt i et OpenAI-array. Den bekraeftede altsaa praecis den
    fejl der gjorde vaerktoejerne ukaldbare for provideren. Nu laeser den det
    sted en OpenAI-compat provider ogsaa laeser.
    """
    names = {(d.get("function") or {}).get("name") for d in TOOL_DEFINITIONS}
    assert "dispatch_to_claude_code" in names
    assert "dispatch_status" in names
    assert "dispatch_cancel" in names


def test_dispatch_definitioner_er_velformede():
    """Uden `type` og `function` afviser en striks provider hele requesten."""
    for d in TOOL_DEFINITIONS:
        navn = (d.get("function") or {}).get("name") or ""
        if navn.startswith("dispatch_"):
            assert d.get("type") == "function", navn
            assert "parameters" in d["function"], navn
