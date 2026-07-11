"""Native-tool lås/lås-op — en runtime allowlist Bjørn styrer.

Jarvis' server-side native tools (core/tools/simple_tools.get_tool_definitions) kan
låses/låses-op pr. navn af owner. Et låst tool fjernes fra tool-listen modellen ser,
så Jarvis hverken kan kalde det (v2/server-loop) eller planlægge det. Rent additivt:
tom liste = intet ændret (alle tools som før).

Tilstand i runtime-state (survives restart), self-safe (kaster aldrig; fail-open =
tool tilladt hvis vi ikke kan læse tilstanden).
"""
from __future__ import annotations

_KEY = "native_tools_disabled"  # list[str] — låste tool-navne


def disabled_tools() -> set[str]:
    """Sættet af låste native tool-navne. Fail-open → tom mængde."""
    try:
        from core.runtime.db_core import get_runtime_state_value
        v = get_runtime_state_value(_KEY, []) or []
        return {str(x) for x in v} if isinstance(v, (list, tuple, set)) else set()
    except Exception:
        return set()


def is_disabled(name: str) -> bool:
    return str(name) in disabled_tools()


def set_tool_disabled(name: str, disabled: bool) -> set[str]:
    """Lås (disabled=True) eller lås-op (False) et native tool. Returnerer det nye sæt."""
    cur = disabled_tools()
    name = str(name)
    if disabled:
        cur.add(name)
    else:
        cur.discard(name)
    try:
        from core.runtime.db_core import set_runtime_state_value
        set_runtime_state_value(_KEY, sorted(cur))
    except Exception:
        pass
    return cur
