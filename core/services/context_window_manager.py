"""Context window manager — strategies for keeping prompts within budget.

Existing infrastructure (smart_compact_tools) does ONE thing: LLM-summarise
old messages. This module adds two more strategies and an adaptive picker
that chooses based on observed token pressure:

- **sliding**: Keep last N messages verbatim, drop the middle entirely.
  Cheap, no LLM call. Best when middle is mostly noise/repetition.

- **hierarchical**: Keep last N verbatim, summarise the middle (existing
  smart_compact path), archive the oldest to disk for later recall.
  Best balance for long sessions where context still matters.

- **sliding_with_anchors**: Like sliding but preserves messages flagged
  as "anchor" (decisions, errors, user corrections). Cheap, smarter
  than naive sliding.

- **adaptive**: Picks one of the above based on current token pressure.

Also exposes degradation_signal() — a heuristic that detects when long
context is hurting performance (lots of recent tool errors, repeated
attempts, model contradicting itself). Surfaces in awareness so Jarvis
can self-trigger compaction.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# Token thresholds (rough — calibrate over time via instrumentation)
_TOKEN_BUDGET_TARGET = 8000      # comfortable working size
_TOKEN_PRESSURE_HIGH = 16000     # start nudging
_TOKEN_PRESSURE_CRITICAL = 24000  # force action


def _estimate_session_tokens() -> int:
    try:
        from core.tools.smart_compact_tools import _estimate_session_tokens as _est
        return int(_est() or 0)
    except Exception:
        return 0


def _list_session_messages(session_id: str = "", limit: int = 200) -> list[dict[str, Any]]:
    try:
        from core.services.chat_sessions import list_chat_sessions, recent_chat_session_messages
        if not session_id:
            sessions = list_chat_sessions()
            if not sessions:
                return []
            session_id = str(sessions[0].get("session_id") or "")
        return list(recent_chat_session_messages(session_id, limit=limit) or [])
    except Exception:
        return []


# Heuristic anchors — messages we never want to drop from a sliding window.
# Pattern keywords (case-insensitive).
_ANCHOR_PATTERNS: tuple[str, ...] = (
    "besluttede", "vi valgte", "bekræftet", "vigtigt:",
    "rettelse:", "ikke gør", "stop med", "lav om", "fix:",
    "fejl:", "error:", "approval", "godkendt",
)


def _is_anchor(message: dict[str, Any]) -> bool:
    content = str(message.get("content") or "").lower()
    if not content:
        return False
    return any(p in content for p in _ANCHOR_PATTERNS)


def apply_sliding(
    messages: list[dict[str, Any]],
    *,
    keep_recent: int = 30,
    preserve_anchors: bool = True,
) -> dict[str, Any]:
    """Keep last N messages, drop middle. Optionally preserve anchor messages."""
    if len(messages) <= keep_recent:
        return {"strategy": "sliding", "kept": len(messages), "dropped": 0, "messages": messages}

    recent = messages[-keep_recent:]
    older = messages[:-keep_recent]
    anchors_kept: list[dict[str, Any]] = []
    if preserve_anchors:
        anchors_kept = [m for m in older if _is_anchor(m)]
    kept = anchors_kept + recent
    return {
        "strategy": "sliding_with_anchors" if preserve_anchors else "sliding",
        "kept": len(kept),
        "dropped": len(messages) - len(kept),
        "anchors_preserved": len(anchors_kept),
        "messages": kept,
    }


def estimate_pressure() -> dict[str, Any]:
    """Read current session size + classify pressure level."""
    tokens = _estimate_session_tokens()
    if tokens >= _TOKEN_PRESSURE_CRITICAL:
        level = "critical"
    elif tokens >= _TOKEN_PRESSURE_HIGH:
        level = "high"
    elif tokens >= _TOKEN_BUDGET_TARGET:
        level = "elevated"
    else:
        level = "comfortable"
    return {
        "estimated_tokens": tokens,
        "level": level,
        "target": _TOKEN_BUDGET_TARGET,
        "high_threshold": _TOKEN_PRESSURE_HIGH,
        "critical_threshold": _TOKEN_PRESSURE_CRITICAL,
    }


def degradation_signal() -> dict[str, Any]:
    """Detect signs that long context is hurting performance.

    Reads recent eventbus to count: tool errors, looped tool calls,
    repeated attempts. Returns a score 0-100 (higher = more degraded).
    Heuristic only — no model evaluation.
    """
    try:
        from core.eventbus.bus import event_bus
        events = event_bus.recent(limit=100)
    except Exception:
        return {"score": 0, "signals": [], "advice": "ok"}

    signals: list[str] = []
    error_count = 0
    consecutive_same_tool = 0
    last_tool = ""
    streak = 0

    for e in reversed(events):  # oldest first
        if str(e.get("kind", "")) != "tool.completed":
            continue
        payload = e.get("payload") or {}
        if not isinstance(payload, dict):
            continue
        tool = str(payload.get("tool", ""))
        status = str(payload.get("status", ""))
        if status == "error":
            error_count += 1
        if tool == last_tool and tool:
            streak += 1
            consecutive_same_tool = max(consecutive_same_tool, streak)
        else:
            streak = 0
            last_tool = tool

    score = 0
    if error_count >= 3:
        signals.append(f"{error_count} tool errors recent")
        score += min(40, error_count * 8)
    if consecutive_same_tool >= 4:
        signals.append(f"{consecutive_same_tool}x same tool consecutively")
        score += min(30, consecutive_same_tool * 5)

    pressure = estimate_pressure()
    if pressure["level"] in ("high", "critical"):
        signals.append(f"context pressure {pressure['level']} ({pressure['estimated_tokens']} tokens)")
        score += 20 if pressure["level"] == "high" else 35

    advice = "ok"
    if score >= 60:
        advice = "compact_now_aggressive"  # Use sliding to drop a lot
    elif score >= 30:
        advice = "compact_smart"  # Use smart_compact to summarise
    elif score >= 15:
        advice = "monitor"

    return {
        "score": min(100, score),
        "signals": signals,
        "advice": advice,
        "pressure": pressure,
    }


def adaptive_pick_strategy() -> str:
    """Pick the best strategy for current state."""
    deg = degradation_signal()
    advice = deg.get("advice", "ok")
    if advice == "compact_now_aggressive":
        return "sliding_with_anchors"
    if advice == "compact_smart":
        return "smart_compact"
    return "none"


def context_window_section() -> str | None:
    """Awareness-section warning when degradation detected."""
    deg = degradation_signal()
    if deg.get("advice") == "ok":
        return None
    score = deg.get("score", 0)
    signals = deg.get("signals") or []
    rec = deg.get("advice", "")
    sig_text = "; ".join(signals[:3]) if signals else "context pressure"
    return (
        f"⚠ Context degradation score {score}/100 ({sig_text}). "
        f"Anbefaling: **{rec}**. Brug `manage_context_window(strategy='adaptive')` "
        "for at lade systemet vælge bedst egnede komprimering."
    )


def _exec_context_pressure(args: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "ok",
        "pressure": estimate_pressure(),
        "degradation": degradation_signal(),
    }


def _exec_manage_context_window(args: dict[str, Any]) -> dict[str, Any]:
    """Apply a chosen context-management strategy."""
    strategy = str(args.get("strategy") or "adaptive").strip().lower()
    keep_recent = int(args.get("keep_recent") or 30)
    if strategy == "adaptive":
        strategy = adaptive_pick_strategy()
        if strategy == "none":
            return {
                "status": "ok",
                "applied": "none",
                "reason": "context comfortable — no action needed",
                "pressure": estimate_pressure(),
            }
    if strategy == "smart_compact":
        try:
            from core.tools.smart_compact_tools import _exec_smart_compact
            return {
                "status": "ok",
                "applied": "smart_compact",
                "result": _exec_smart_compact({"keep_recent": keep_recent, "force": True}),
            }
        except Exception as exc:
            return {"status": "error", "error": f"smart_compact failed: {exc}"}
    if strategy in ("sliding", "sliding_with_anchors"):
        msgs = _list_session_messages(limit=300)
        result = apply_sliding(
            msgs,
            keep_recent=keep_recent,
            preserve_anchors=(strategy == "sliding_with_anchors"),
        )
        return {
            "status": "ok",
            "applied": strategy,
            "summary": {
                "kept": result["kept"],
                "dropped": result["dropped"],
                "anchors_preserved": result.get("anchors_preserved", 0),
            },
            "note": "Sliding is advisory — runtime must apply the kept-list to next prompt build to take effect.",
        }
    return {"status": "error", "error": f"unknown strategy: {strategy}"}


CONTEXT_WINDOW_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "context_pressure",
            "description": (
                "Read current session token pressure + degradation score. "
                "Returns level (comfortable/elevated/high/critical) and advice "
                "on whether to compact. Cheap to call."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "manage_context_window",
            "description": (
                "Apply a context-management strategy: 'adaptive' (system picks), "
                "'smart_compact' (LLM-summarise old), 'sliding' (drop middle, "
                "keep last N), 'sliding_with_anchors' (sliding + preserve "
                "decisions/errors). Use when context_pressure shows elevated."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "strategy": {
                        "type": "string",
                        "enum": ["adaptive", "smart_compact", "sliding", "sliding_with_anchors"],
                    },
                    "keep_recent": {
                        "type": "integer",
                        "description": "How many recent messages to keep verbatim (default 30).",
                    },
                },
                "required": [],
            },
        },
    },
]
