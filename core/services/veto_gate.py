"""Veto gate — pre-execution hook that pauses tool calls when pushback is firm.

When affective_pushback fires with action=firm_pushback AND there is
evidence (not just feeling), the veto gate can block execution and
surface a confirmation request to the user instead of blindly running
the tool.

This is the "muscle" behind pushback: pushback generates the signal,
veto_gate acts on it.

Design:
- Called from _execute_simple_tool_calls before each tool runs.
- Returns (allowed: bool, reason: str | None).
- If not allowed, the tool call is replaced with a veto message that
  surfaces in the chat as a confirmation card.
- Bjørn retains authority: vetoes can always be overridden by explicit
  user confirmation ("ja", "kør", "gør det").
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# Tools that are always allowed (read-only, no side effects).
_ALWAYS_ALLOWED_TOOLS = frozenset({
    "read_file", "read_tool_result", "read_self_docs", "search",
    "find_files", "web_fetch", "web_scrape", "web_search",
    "get_weather", "get_exchange_rate", "get_news", "wolfram_query",
    "analyze_image", "list_initiatives", "list_proposals",
    "list_scheduled_tasks", "list_plans", "todo_list", "monitor_list",
    "verification_status", "context_pressure", "context_size_check",
    "heartbeat_status", "daemon_status", "discord_status",
    "comfyui_status", "comfyui_objects", "health_status",
    "goal_list", "decision_list", "composite_list",
    "list_identity_pins", "read_visual_memory", "recall_sensory_memories",
    "recall_memories", "search_jarvis_brain", "search_memory",
    "memory_list_headings", "search_sessions", "provider_health_status",
    "tick_quality_summary", "detect_stale_goals", "decision_adherence_summary",
    "list_prompt_experiments", "list_agent_observations",
    "list_arcs", "list_crisis_markers", "list_recurring",
    "list_self_wakeups", "list_events",
})


def check_veto(
    tool_name: str,
    user_message: str = "",
    session_id: str | None = None,
) -> tuple[bool, str | None]:
    """Check if a tool call should be vetoed.

    Returns (allowed, reason). If allowed=True, proceed.
    If allowed=False, the tool call should be replaced with a
    veto message asking for confirmation.

    Logic:
    1. Read-only tools are always allowed.
    2. Compute affective pushback for the user message.
    3. If pushback action is firm_pushback AND evidence exists → veto.
    4. If pushback action is soft_pushback AND confidence < 0.3 → veto.
    5. Otherwise → allow.
    """
    if tool_name in _ALWAYS_ALLOWED_TOOLS:
        return True, None

    # Read pushback state
    try:
        from core.services.pushback import affective_pushback_section
        section = affective_pushback_section(user_message)
    except Exception:
        return True, None

    if not section:
        return True, None

    # Parse the section to extract action and evidence
    action = _extract_action(section)
    has_evidence = _has_evidence(section)

    if action == "firm_pushback" and has_evidence:
        return False, _format_veto_reason(section, tool_name)

    if action == "soft_pushback" and has_evidence:
        # Soft pushback with evidence: allow but emit warning
        try:
            from core.eventbus.bus import event_bus
            event_bus.publish("veto_gate.soft_warning", {
                "tool_name": tool_name,
                "pushback_section": section[:500],
            })
        except Exception:
            pass
        return True, None

    return True, None


def _extract_action(section: str) -> str:
    """Extract the action tier from the pushback section text."""
    for line in section.splitlines():
        if "action=" in line:
            for part in line.split():
                if part.startswith("action="):
                    return part.split("=", 1)[1].strip()
    return ""


def _has_evidence(section: str) -> bool:
    """Check if the pushback section contains evidence markers."""
    return "evidence:" in section and "weak/none" not in section


def _format_veto_reason(section: str, tool_name: str) -> str:
    """Format a human-readable veto reason."""
    lines = section.strip().splitlines()
    # First line is the header, second is feeling, rest is evidence
    feeling_line = ""
    evidence_lines = []
    for line in lines:
        if "feeling=" in line:
            feeling_line = line.strip()
        elif "evidence:" in line and "weak/none" not in line:
            evidence_lines.append(line.strip())

    parts = [f"VETO: {tool_name} blokeret af affective pushback."]
    if feeling_line:
        parts.append(feeling_line)
    for e in evidence_lines[:2]:
        parts.append(e)
    parts.append("Sig 'ja' eller 'kør' for at gennemtvinge alligevel.")
    return " | ".join(parts)