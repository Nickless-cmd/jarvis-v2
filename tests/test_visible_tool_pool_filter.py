from __future__ import annotations

from core.tools.copilot_tool_pruning import select_tools_for_visible
from core.tools.simple_tools import get_tool_definitions


def _tool_name(tool_def: dict) -> str:
    return str((tool_def.get("function") or tool_def).get("name") or "")


def test_visible_tool_pool_is_small_and_has_lazy_loader():
    selected = select_tools_for_visible(get_tool_definitions(), user_message="hej")
    names = [_tool_name(item) for item in selected]

    assert len(names) <= 48
    assert "load_more_tools" in names
    assert {"read_file", "write_file", "edit_file", "bash", "search"}.issubset(names)


def test_visible_tool_pool_is_cache_stable_across_user_messages():
    all_defs = get_tool_definitions()
    greeting = [_tool_name(item) for item in select_tools_for_visible(
        all_defs, user_message="hej hvordan går det?"
    )]
    coding = [_tool_name(item) for item in select_tools_for_visible(
        all_defs, user_message="ret buggen i prompt contract og kør pytest"
    )]

    assert greeting == coding


def test_visible_tool_pool_keeps_catalog_order_for_deepseek_cache():
    all_defs = get_tool_definitions()
    original_order = {_tool_name(item): idx for idx, item in enumerate(all_defs)}
    selected = [_tool_name(item) for item in select_tools_for_visible(all_defs)]

    assert selected == sorted(selected, key=lambda name: original_order[name])
