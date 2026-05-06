"""Smoke check that the selector returns a usable ToolSelection."""
from core.services.tool_router import select_tools


def test_select_tools_returns_selection_for_visible_lane():
    sel = select_tools(
        user_message="hej hvad sker der i dag?",
        session_id=None, lane="visible",
    )
    # Always returns something, never None
    assert sel is not None
    assert isinstance(sel.selected_names, list)
    # Either we got a selection or fell back; both are valid
    if not sel.fallback_used:
        # If selection happened, load_more_tools should always be present
        # (it's in the pinned set, so it's in always-core)
        assert "load_more_tools" in sel.selected_names


def test_select_tools_fallback_on_empty_message():
    sel = select_tools(user_message="", session_id=None, lane="visible")
    assert sel.fallback_used  # empty message → no clarity → fallback
