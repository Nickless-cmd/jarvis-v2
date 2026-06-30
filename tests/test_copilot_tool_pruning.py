"""Tool-pruning for the visible/copilot lanes.

Cache regression: the visible lane keyword-routed the tool SET per user message
(keyword_scores + recent usage), so the ~17k-token tool block changed turn-to-turn
and broke DeepSeek's prefix cache on keyword-heavy turns. select_tools_for_visible
now passes stable_only=True → deterministic set every turn. load_more_tools must be
in the always-on core so Jarvis can still reach the long tail on demand.
"""
from __future__ import annotations

from core.tools import copilot_tool_pruning as ctp


def _make_tools(n_extra: int = 40) -> list[dict]:
    """Tier-1 tools + extra non-tier-1 tools, exceeding MAX_TOOLS so pruning runs."""
    tools = [{"function": {"name": name}} for name in sorted(ctp.TIER_1_ALWAYS_ON)]
    tools += [{"function": {"name": f"zz_extra_{i:02d}"}} for i in range(n_extra)]
    return tools


def _names(sel: list[dict]) -> list[str]:
    return [(t.get("function") or {}).get("name") for t in sel]


def test_load_more_tools_in_tier1():
    # Escape-hatch to the ~316 non-sent tools must always be available.
    assert "load_more_tools" in ctp.TIER_1_ALWAYS_ON


def test_visible_set_is_deterministic_across_messages():
    tools = _make_tools()
    assert len(tools) > ctp.MAX_TOOLS  # ensure pruning actually triggers
    a = ctp.select_tools_for_visible(tools, user_message="hej hvordan har du det", session_id="s")
    b = ctp.select_tools_for_visible(
        tools,
        user_message="searche google sende discord scheduled wakeup screenshot commit",
        session_id="s",
    )
    # Byte-identical selection regardless of (keyword-heavy) message → cacheable.
    assert _names(a) == _names(b)
    assert len(a) == ctp.MAX_TOOLS


def test_stable_only_ignores_user_message():
    tools = _make_tools()
    a = ctp.select_tools_for_copilot(tools, user_message="weather forecast", stable_only=True)
    b = ctp.select_tools_for_copilot(tools, user_message="git commit push deploy", stable_only=True)
    assert _names(a) == _names(b)


def test_tier1_always_included_when_pruned():
    tools = _make_tools()
    sel = set(_names(ctp.select_tools_for_visible(tools, user_message="x", session_id="s")))
    # Every Tier-1 tool present in the catalog survives pruning.
    for name in ctp.TIER_1_ALWAYS_ON:
        assert name in sel


def test_full_catalog_under_cap_returned_unchanged():
    tools = [{"function": {"name": f"t{i}"}} for i in range(10)]
    out = ctp.select_tools_for_copilot(tools, user_message="anything", max_tools=128)
    assert _names(out) == _names(tools)
