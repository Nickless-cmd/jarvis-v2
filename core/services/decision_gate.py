"""Decision gate — pre-execution decision conflict detection.

Cross-checks a user request against active behavioral decisions
BEFORE execution, not just in the prompt. If a tool call would
contradict an active decision, the gate blocks it and surfaces
the conflict for user confirmation.

This gives decisions "teeth" — they can actually prevent actions
that violate commitments, not just be text in the prompt.
"""
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


# Tools whose results are used to check decisions (not blocked themselves).
_META_TOOLS = frozenset({
    "decision_list", "decision_get", "decision_review",
    "list_proposals", "list_plans", "todo_list",
})


def check_decision_gate(
    tool_name: str,
    tool_args: dict[str, Any] | None = None,
    user_message: str = "",
) -> tuple[bool, str | None]:
    """Check if a tool call conflicts with active decisions.

    Returns (allowed, reason). If allowed=False, the call is blocked
    and the reason should be surfaced to the user.

    Logic:
    1. Meta/decision tools are always allowed.
    2. Load active decisions.
    3. For each decision, check if the tool call + args would violate it.
    4. If conflict found → block with reason.
    5. Otherwise → allow.
    """
    if tool_name in _META_TOOLS:
        return True, None

    try:
        from core.services.behavioral_decisions import list_active_decisions
        decisions = list_active_decisions(limit=10) or []
    except Exception as _exc:
        # Fail-open synlighed (audit 2026-07-04): kan gaten ikke læse aktive beslutninger
        # tillader den handlingen — men det MÅ ikke være tavst, ellers kan Jarvis bryde
        # egne forpligtelser uden spor. Flag fail-open FØR return. Self-safe: incident-
        # loggen kaster aldrig, og fail-open-adfærden (return True, None) er uændret.
        try:
            from core.runtime.db_central_incidents import record_central_incident
            record_central_incident(
                cluster="commit", nerve="decision_gate", kind="fail_open",
                severity="error",
                message=f"check_decision_gate kunne ikke læse beslutninger → fail-OPEN "
                        f"for tool={tool_name}: {type(_exc).__name__}: {_exc}"[:300],
            )
        except Exception:
            pass
        return True, None

    if not decisions:
        return True, None

    # Build a combined context string from tool name + args + user message
    context = _build_context(tool_name, tool_args, user_message)

    conflicts: list[str] = []
    for d in decisions:
        directive = str(d.get("directive") or "").strip()
        if not directive:
            continue
        conflict = _detect_conflict(directive, context, d)
        if conflict:
            decision_id = str(d.get("decision_id") or "unknown")
            conflicts.append(f"[{decision_id[:8]}] {directive[:60]} — {conflict}")

    if not conflicts:
        return True, None

    # Multiple conflicts: surface the top 2
    top = conflicts[:2]
    reason = (
        f"DECISION GATE: {len(conflicts)} aktiv(e) forpligtelse(r) i konflikt. "
        + " | ".join(top)
        + " — Sig 'alligevel' for at gennemtvinge."
    )

    # Emit telemetry
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("decision_gate.conflict", {
            "tool_name": tool_name,
            "conflict_count": len(conflicts),
            "conflicts": conflicts[:3],
        })
    except Exception:
        pass

    return False, reason


# Grader af blok (Commit-cluster, 2026-06-22): en konflikt med en HØJ-prioritets-
# beslutning hård-blokerer (RED); en konflikt med kun lav-prioritets-beslutninger blød-
# advarer men tillader (YELLOW). Tærskel = 50 (= create_decision-default), så nuværende
# blokerings-adfærd bevares for normale beslutninger; kun eksplicit lav-prioritet softer.
_HARD_BLOCK_PRIORITY = 50


def evaluate_decision_conflict(
    tool_name: str,
    tool_args: dict[str, Any] | None = None,
    user_message: str = "",
) -> tuple[str, str | None]:
    """Graderet decision-conflict. Returnerer (severity, reason):
      'hard' → RED (blokér; konflikt med beslutning ≥ tærskel-prioritet)
      'soft' → YELLOW (advar men tillad; kun lav-prioritets-konflikt)
      'none' → GREEN (ingen konflikt)
    """
    if tool_name in _META_TOOLS:
        return "none", None
    try:
        from core.services.behavioral_decisions import list_active_decisions
        decisions = list_active_decisions(limit=10) or []
    except Exception as _exc:
        # Fail-open synlighed (audit 2026-07-04): graderet-varianten fejler også STILLE til
        # 'none' (GREEN) → Jarvis kan bryde en forpligtelse uden spor. Flag FØR return.
        # Self-safe: incident-loggen kaster aldrig; fail-open-adfærden ('none', None) uændret.
        try:
            from core.runtime.db_central_incidents import record_central_incident
            record_central_incident(
                cluster="commit", nerve="decision_gate", kind="fail_open",
                severity="error",
                message=f"evaluate_decision_conflict kunne ikke læse beslutninger → "
                        f"fail-OPEN for tool={tool_name}: {type(_exc).__name__}: {_exc}"[:300],
            )
        except Exception:
            pass
        return "none", None
    if not decisions:
        return "none", None

    context = _build_context(tool_name, tool_args, user_message)
    conflicts: list[str] = []
    max_priority = 0
    for d in decisions:
        directive = str(d.get("directive") or "").strip()
        if not directive:
            continue
        if _detect_conflict(directive, context, d):
            decision_id = str(d.get("decision_id") or "unknown")
            conflicts.append(f"[{decision_id[:8]}] {directive[:60]}")
            max_priority = max(max_priority, int(d.get("priority") or 0))

    if not conflicts:
        return "none", None

    severity = "hard" if max_priority >= _HARD_BLOCK_PRIORITY else "soft"
    top = " | ".join(conflicts[:2])
    if severity == "hard":
        reason = (f"DECISION GATE (blok): {len(conflicts)} forpligtelse(r) i konflikt "
                  f"— {top} — Sig 'alligevel' for at gennemtvinge.")
    else:
        reason = (f"DECISION GATE (blød advarsel): tangerer {len(conflicts)} lav-prioritets-"
                  f"forpligtelse(r) — {top}. Kører, men vær opmærksom.")
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("decision_gate.conflict", {
            "tool_name": tool_name, "severity": severity,
            "conflict_count": len(conflicts), "max_priority": max_priority,
        })
    except Exception:
        pass
    return severity, reason


def _build_context(
    tool_name: str,
    tool_args: dict[str, Any] | None,
    user_message: str,
) -> str:
    """Build a context string for conflict detection."""
    parts = [tool_name]
    if tool_args:
        for key in ("path", "command", "content", "text", "old_text", "new_text"):
            val = tool_args.get(key)
            if val:
                parts.append(str(val)[:200])
    if user_message:
        parts.append(user_message[:300])
    return " ".join(parts).lower()


def _detect_conflict(directive: str, context: str, decision: dict) -> str | None:
    """Detect if the context conflicts with a decision directive.

    Uses heuristic pattern matching:
    - If directive says "undgå/ikke/stop/avoid X" and context contains X → conflict
    - If directive says "altid/always X" and context suggests NOT doing X → conflict
    """
    directive_lower = directive.lower()
    context_lower = context.lower()

    # Pattern: avoidance directive — "undgå X", "ikke X", "stop X"
    avoid_match = re.search(
        r"\b(undgå|undlad|ikke|stop|avoid|don'?t|never)\b\s+(?:at\s+|to\s+)?([a-zæøå]+(?:\s+[a-zæøå]+){0,4})",
        directive_lower,
    )
    if avoid_match:
        target = avoid_match.group(2).strip()
        if target and target in context_lower:
            return f"handling matcher '{target}' som forpligtelsen siger at undgå"

    # Pattern: imperative directive — "altid X" and context suggests skipping
    always_match = re.search(
        r"\b(altid|always|skal altid|must always)\b\s+(?:at\s+)?([a-zæøå]+(?:\s+[a-zæøå]+){0,3})",
        directive_lower,
    )
    if always_match:
        target = always_match.group(2).strip()
        # Check if the context explicitly skips/avoids the target
        skip_patterns = [f"uden {target}", f"skip {target}", f"spring {target}", f"ikke {target}"]
        for sp in skip_patterns:
            if sp in context_lower:
                return f"context foreslår at springe '{target}' over som forpligtelsen kræver"

    return None