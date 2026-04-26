"""Self-monitor — anti-loop detection from tool call history.

Three failure modes for an LLM in an agentic loop:

1. **Repeating a failing call.** Same tool, same(ish) arguments, status=error
   three or four times in a row. Without intervention the model often keeps
   trying with a one-character tweak each time. Anti-loop alert breaks the
   pattern by naming it explicitly: "you've called X N times with errors —
   try a different approach."

2. **Burning tools without progress.** Lots of recent tool calls but no
   visible result text — sign of the model thrashing. Less actionable than
   the loop case but worth surfacing.

3. **Same tool every time.** Calling search 12 times in a row when the
   answer was in the first response. Suggests the model isn't reading
   results.

This module reads from the eventbus (tool.invoked / tool.completed events)
which doesn't require any new wiring — those events already fire.

Surfaced as a single prompt section so the model sees "warning: you've
done X" and can self-correct. Cheap, idempotent, no state to persist.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_LOOK_BACK_EVENTS = 30
_LOOP_THRESHOLD_REPEATS = 3
_THRASH_THRESHOLD = 8  # >=N tool calls in window with no spacing


def _recent_tool_events(limit: int = _LOOK_BACK_EVENTS) -> list[dict[str, Any]]:
    try:
        from core.eventbus.bus import event_bus
    except Exception:
        return []
    try:
        events = event_bus.recent(limit=limit * 3)
    except Exception:
        return []
    out = []
    for e in events:
        kind = str(e.get("kind", ""))
        if kind == "tool.completed" or kind == "tool.invoked":
            out.append(e)
        if len(out) >= limit:
            break
    return out


def _looped_tools(events: list[dict[str, Any]]) -> list[tuple[str, int]]:
    """Find tools that errored repeatedly in succession.

    Returns list of (tool_name, error_count) for tools where the most-recent
    N completions were all errors and N >= _LOOP_THRESHOLD_REPEATS.
    """
    by_tool: dict[str, list[str]] = {}
    for e in events:  # newest first
        if e.get("kind") != "tool.completed":
            continue
        payload = e.get("payload") or {}
        if not isinstance(payload, dict):
            continue
        tool = str(payload.get("tool", ""))
        status = str(payload.get("status", ""))
        if not tool:
            continue
        by_tool.setdefault(tool, []).append(status)
    looped: list[tuple[str, int]] = []
    for tool, statuses in by_tool.items():
        # Only look at the most recent run; consecutive errors counted from newest.
        consecutive = 0
        for s in statuses:
            if s == "error":
                consecutive += 1
            else:
                break
        if consecutive >= _LOOP_THRESHOLD_REPEATS:
            looped.append((tool, consecutive))
    return looped


def _thrashing_score(events: list[dict[str, Any]]) -> int:
    """Crude thrash signal: count of tool.invoked in the recent window."""
    return sum(1 for e in events if e.get("kind") == "tool.invoked")


def self_monitor_section() -> str | None:
    """Format anti-loop / thrash signals as a prompt section, or None."""
    events = _recent_tool_events(limit=_LOOK_BACK_EVENTS)
    if not events:
        return None
    notes: list[str] = []
    looped = _looped_tools(events)
    for tool, count in looped:
        notes.append(
            f"⚠ Du har lige kaldt **{tool}** {count} gange i træk og fået "
            f"fejl hver gang. Stop med at gentage — læs den seneste fejl, "
            f"og prøv en anden tilgang (andet tool, anden vinkel, eller "
            f"spørg brugeren)."
        )
    thrash = _thrashing_score(events)
    if thrash >= _THRASH_THRESHOLD and not looped:
        notes.append(
            f"⚠ {thrash} tool-calls i seneste vindue uden synlig progress. "
            f"Stop og opsummer hvad du har lært før næste call."
        )
    if not notes:
        return None
    return "Selv-monitor (advarsler fra dit eget tool-call mønster):\n" + "\n".join(notes)
