"""Proactive context governor — auto-trigger compaction + sub-agent slicing.

Existing context_window_manager exposes strategies (sliding/smart_compact),
but they only fire when the model decides to call them. Jarvis often
DOESN'T notice degradation until it hurts.

This module makes context management proactive:

1. **Auto-trigger at threshold** — if context usage crosses 70% of
   target, automatically run smart_compact in next prompt build.
   Hooked into prompt_contract pre-build via should_auto_compact().

2. **Sub-agent context slicing** — when spawn_agent_task is called with
   a goal, this module returns a SLICE of context (not full session)
   tailored to the agent's task. Uses memory_recall_engine to pick
   most relevant past messages + adds active goals + relevant memories.

3. **Context versioning** — each compaction stores the "before" snapshot
   in state_store. Tool to backtrace decisions: list_context_versions,
   recall_context_version.

The 70% threshold is calibrated low because compaction takes time —
we want to start it before pressure becomes critical. Configurable
via runtime settings.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.runtime.state_store import load_json, save_json

logger = logging.getLogger(__name__)


_AUTO_COMPACT_THRESHOLD_PCT = 70   # of target token budget
_AUTO_COMPACT_COOLDOWN_SECONDS = 300  # don't re-trigger within 5 min
_VERSION_STORE_KEY = "context_versions"
_MAX_VERSIONS_KEPT = 30


_LAST_AUTO_COMPACT_TS = 0.0


# ── Auto-trigger ──────────────────────────────────────────────────────


def should_auto_compact() -> dict[str, Any]:
    """Decide whether prompt_contract should trigger compaction now."""
    import time
    global _LAST_AUTO_COMPACT_TS

    try:
        from core.services.context_window_manager import estimate_pressure
        pressure = estimate_pressure()
    except Exception as exc:
        return {"should_compact": False, "reason": f"pressure check failed: {exc}"}

    tokens = int(pressure.get("estimated_tokens") or 0)
    target = int(pressure.get("target") or 8000)
    pct = (tokens / target * 100) if target > 0 else 0

    if pct < _AUTO_COMPACT_THRESHOLD_PCT:
        return {
            "should_compact": False,
            "reason": f"only {pct:.0f}% of target ({tokens}/{target})",
            "tokens": tokens,
            "percent": round(pct, 1),
        }

    now = time.time()
    if (now - _LAST_AUTO_COMPACT_TS) < _AUTO_COMPACT_COOLDOWN_SECONDS:
        return {
            "should_compact": False,
            "reason": "auto-compact cooldown active",
            "tokens": tokens,
            "percent": round(pct, 1),
        }

    return {
        "should_compact": True,
        "reason": f"context at {pct:.0f}% of target — proactive compaction",
        "tokens": tokens,
        "percent": round(pct, 1),
    }


def auto_compact_if_needed() -> dict[str, Any]:
    """Run compaction if threshold crossed. Idempotent (cooldown protected)."""
    import time
    global _LAST_AUTO_COMPACT_TS

    decision = should_auto_compact()
    if not decision.get("should_compact"):
        return {"status": "ok", "compacted": False, **decision}

    # Snapshot before compacting
    version_id = save_context_version(reason="pre-auto-compact")

    try:
        from core.tools.smart_compact_tools import _exec_smart_compact
        result = _exec_smart_compact({"force": True})
    except Exception as exc:
        return {"status": "error", "error": f"compact failed: {exc}", "version_id": version_id}

    _LAST_AUTO_COMPACT_TS = time.time()

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            "context.auto_compacted",
            {"trigger_reason": decision.get("reason"), "version_id": version_id},
        )
    except Exception:
        pass

    return {
        "status": "ok",
        "compacted": True,
        "version_id": version_id,
        "compact_result": result,
        **decision,
    }


# ── Sub-agent context slicing ──────────────────────────────────────────


def build_subagent_context_slice(
    *,
    role: str,
    goal: str,
    max_chars: int = 4000,
) -> dict[str, Any]:
    """Compose a tailored context slice for a sub-agent based on goal.

    Returns:
        {
          "goal": str,
          "active_goals": [...],
          "relevant_memories": [...],
          "recent_decisions": [...],
          "compact_text": str (the assembled slice)
        }
    """
    parts: list[str] = []
    out: dict[str, Any] = {"goal": goal, "role": role}

    # 1. Always include the agent's specific goal
    parts.append(f"## Din opgave\n{goal}")

    # 2. Active autonomous goals (top-level context)
    try:
        from core.services.autonomous_goals import list_goals
        active = list_goals(status="active", parent_id="any", limit=3)
        if active:
            out["active_goals"] = [g.get("title") for g in active]
            goal_lines = [f"- {g.get('title')} ({g.get('priority')})" for g in active]
            parts.append("## Jarvis' aktive mål\n" + "\n".join(goal_lines))
    except Exception:
        out["active_goals"] = []

    # 3. Most relevant memories for this goal
    try:
        from core.services.memory_recall_engine import unified_recall
        recall = unified_recall(query=goal, total_limit=4, with_mood=False)
        memories = recall.get("results") or []
        if memories:
            out["relevant_memories"] = [m.get("text", "")[:120] for m in memories]
            mem_lines = [f"- [{m.get('source', '?')}] {m.get('text', '')[:200]}" for m in memories]
            parts.append("## Relevante hukommelser\n" + "\n".join(mem_lines))
    except Exception:
        out["relevant_memories"] = []

    compact = "\n\n".join(parts)
    if len(compact) > max_chars:
        compact = compact[:max_chars] + "\n[...truncated...]"
    out["compact_text"] = compact
    out["chars"] = len(compact)
    return out


# ── Context versioning ────────────────────────────────────────────────


def _load_versions() -> list[dict[str, Any]]:
    raw = load_json(_VERSION_STORE_KEY, [])
    if not isinstance(raw, list):
        return []
    return [v for v in raw if isinstance(v, dict)]


def _save_versions(versions: list[dict[str, Any]]) -> None:
    save_json(_VERSION_STORE_KEY, versions[-_MAX_VERSIONS_KEPT:])


def save_context_version(*, reason: str = "") -> str:
    """Snapshot the current session state. Returns version_id."""
    version_id = f"ctx-{uuid4().hex[:12]}"
    snapshot: dict[str, Any] = {
        "version_id": version_id,
        "reason": reason,
        "captured_at": datetime.now(UTC).isoformat(),
    }
    try:
        from core.tools.smart_compact_tools import _estimate_session_tokens
        snapshot["tokens_at_snapshot"] = _estimate_session_tokens()
    except Exception:
        snapshot["tokens_at_snapshot"] = 0
    try:
        from core.services.chat_sessions import list_chat_sessions, recent_chat_session_messages
        sessions = list_chat_sessions()
        if sessions:
            sid = str(sessions[0].get("session_id") or "")
            msgs = recent_chat_session_messages(sid, limit=80)
            snapshot["session_id"] = sid
            snapshot["message_count"] = len(msgs)
            # Store only first 200 chars of each message — enough for backtrace
            snapshot["message_excerpts"] = [
                {
                    "role": str(m.get("role", "")),
                    "content": str(m.get("content", ""))[:300],
                }
                for m in msgs[-30:]
            ]
    except Exception as exc:
        logger.debug("version snapshot: session read failed: %s", exc)

    versions = _load_versions()
    versions.append(snapshot)
    _save_versions(versions)
    return version_id


def list_context_versions(*, limit: int = 20) -> list[dict[str, Any]]:
    versions = _load_versions()
    summaries = [
        {
            "version_id": v.get("version_id"),
            "reason": v.get("reason"),
            "captured_at": v.get("captured_at"),
            "tokens_at_snapshot": v.get("tokens_at_snapshot"),
            "message_count": v.get("message_count", 0),
        }
        for v in versions[-limit:]
    ]
    return list(reversed(summaries))  # most recent first


def recall_context_version(version_id: str) -> dict[str, Any] | None:
    versions = _load_versions()
    for v in versions:
        if v.get("version_id") == version_id:
            return v
    return None


# ── Tool exposure ─────────────────────────────────────────────────────


def _exec_should_auto_compact(args: dict[str, Any]) -> dict[str, Any]:
    return should_auto_compact()


def _exec_auto_compact_if_needed(args: dict[str, Any]) -> dict[str, Any]:
    return auto_compact_if_needed()


def _exec_build_subagent_context(args: dict[str, Any]) -> dict[str, Any]:
    return build_subagent_context_slice(
        role=str(args.get("role") or "researcher"),
        goal=str(args.get("goal") or ""),
        max_chars=int(args.get("max_chars") or 4000),
    )


def _exec_list_context_versions(args: dict[str, Any]) -> dict[str, Any]:
    return {"status": "ok", "versions": list_context_versions(limit=int(args.get("limit") or 20))}


def _exec_recall_context_version(args: dict[str, Any]) -> dict[str, Any]:
    v = recall_context_version(str(args.get("version_id") or ""))
    if v is None:
        return {"status": "error", "error": "version not found"}
    return {"status": "ok", "version": v}


PROACTIVE_CONTEXT_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "auto_compact_check",
            "description": "Check if context auto-compaction is currently warranted (>=70% of target tokens, no cooldown).",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "auto_compact_run",
            "description": "Run auto-compaction now if threshold crossed. Snapshots context before compacting (versioned).",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "build_subagent_context",
            "description": (
                "Compose a tailored context slice for a sub-agent based on its "
                "goal. Includes: goal, active_goals, relevant_memories from "
                "unified_recall. Use BEFORE spawn_agent_task to reduce token "
                "waste — agent sees only what matters."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "role": {"type": "string"},
                    "goal": {"type": "string"},
                    "max_chars": {"type": "integer"},
                },
                "required": ["role", "goal"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_context_versions",
            "description": "List recent context snapshots (saved before compactions). For backtrace.",
            "parameters": {"type": "object", "properties": {"limit": {"type": "integer"}}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recall_context_version",
            "description": "Retrieve a specific context version's full snapshot (with message excerpts).",
            "parameters": {
                "type": "object",
                "properties": {"version_id": {"type": "string"}},
                "required": ["version_id"],
            },
        },
    },
]
