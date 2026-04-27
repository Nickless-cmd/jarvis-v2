"""Autonomous goals — persistent top-level goals with decomposition.

Layer above agent-goals (per-spawn) and initiatives (queued tasks). These
are *Jarvis' own long-running goals* — what he's working toward over
days/weeks. Each goal can be:

- **Manually set** by user ("understand the new memory architecture")
- **Self-generated** from dreams/reflections by goal_signal_synthesizer
- **Decomposed** into sub-goals via LLM

Stored in JSON via state_store (consistent with other persisted state).
Hierarchical: each goal has parent_id (None = top-level).

Status: pending → active → blocked → achieved → archived
Priority: critical | high | medium | low
Source: user | dream | reflection | self-initiated | decomposition
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.runtime.state_store import load_json, save_json

logger = logging.getLogger(__name__)

_STATE_KEY = "autonomous_goals"
_VALID_STATUSES = {"pending", "active", "blocked", "achieved", "archived"}
_VALID_PRIORITIES = {"critical", "high", "medium", "low"}


def _load() -> dict[str, dict[str, Any]]:
    raw = load_json(_STATE_KEY, {})
    if not isinstance(raw, dict):
        return {}
    return {str(k): v for k, v in raw.items() if isinstance(v, dict)}


def _save(goals: dict[str, dict[str, Any]]) -> None:
    save_json(_STATE_KEY, goals)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def create_goal(
    *,
    title: str,
    description: str = "",
    parent_id: str | None = None,
    priority: str = "medium",
    source: str = "user",
) -> dict[str, Any]:
    """Create a new goal. Returns the created entry."""
    title = (title or "").strip()
    if not title:
        return {"status": "error", "error": "title is required"}
    if priority not in _VALID_PRIORITIES:
        priority = "medium"
    goals = _load()
    goal_id = f"goal-{uuid4().hex[:12]}"
    entry = {
        "goal_id": goal_id,
        "title": title[:200],
        "description": (description or "")[:1000],
        "parent_id": str(parent_id) if parent_id else None,
        "status": "pending",
        "priority": priority,
        "source": str(source),
        "created_at": _now(),
        "updated_at": _now(),
        "achieved_at": None,
        "sub_goal_ids": [],
    }
    goals[goal_id] = entry
    if parent_id and parent_id in goals:
        parent = goals[parent_id]
        parent["sub_goal_ids"] = list(parent.get("sub_goal_ids") or []) + [goal_id]
        parent["updated_at"] = _now()
    _save(goals)
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("goal.created", {"goal_id": goal_id, "title": title, "source": source})
    except Exception:
        pass
    return {"status": "ok", "goal": entry}


def update_goal_status(goal_id: str, new_status: str) -> dict[str, Any]:
    if new_status not in _VALID_STATUSES:
        return {"status": "error", "error": f"invalid status: {new_status}"}
    goals = _load()
    if goal_id not in goals:
        return {"status": "error", "error": "goal not found"}
    g = goals[goal_id]
    old = g.get("status")
    g["status"] = new_status
    g["updated_at"] = _now()
    if new_status == "achieved":
        g["achieved_at"] = _now()
    _save(goals)
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("goal.status_changed", {"goal_id": goal_id, "from": old, "to": new_status})
    except Exception:
        pass
    return {"status": "ok", "goal": g}


def list_goals(
    *,
    status: str | None = None,
    priority: str | None = None,
    parent_id: str | None = "any",
    limit: int = 50,
) -> list[dict[str, Any]]:
    """List goals matching filters. parent_id='any' = no filter, None = top-level only."""
    goals = list(_load().values())
    if status:
        goals = [g for g in goals if g.get("status") == status]
    if priority:
        goals = [g for g in goals if g.get("priority") == priority]
    if parent_id != "any":
        goals = [g for g in goals if g.get("parent_id") == parent_id]
    # Sort: priority order, then most recent first
    prio_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    goals.sort(key=lambda g: (prio_rank.get(g.get("priority", "medium"), 9), g.get("updated_at", "")), reverse=False)
    return goals[:limit]


def decompose_goal(goal_id: str) -> dict[str, Any]:
    """Use cheap-lane LLM to split a goal into 3-5 concrete sub-goals."""
    goals = _load()
    if goal_id not in goals:
        return {"status": "error", "error": "goal not found"}
    g = goals[goal_id]
    title = g.get("title", "")
    desc = g.get("description", "")

    prompt = (
        f"Split dette mål i 3-5 konkrete sub-mål. Svar KUN med en nummereret "
        f"liste, ét sub-mål per linje, ingen indledning.\n\n"
        f"Mål: {title}\n"
        f"Beskrivelse: {desc}\n\n"
        "Sub-mål skal være konkrete, testbare, og hver kunne afsluttes på max et par dage."
    )
    try:
        from core.services.daemon_llm import daemon_llm_call
        body = daemon_llm_call(prompt, max_len=800, fallback="", daemon_name="goal_decomposition")
    except Exception as exc:
        return {"status": "error", "error": f"llm call failed: {exc}"}
    if not body or len(body.strip()) < 10:
        return {"status": "failed", "reason": "llm output empty"}

    # Parse numbered list
    sub_titles: list[str] = []
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        # Strip leading "1." / "1)" / "- " etc.
        for prefix in ("- ", "* "):
            if line.startswith(prefix):
                line = line[len(prefix):]
                break
        if line and line[0].isdigit():
            for sep in (". ", ") ", ": "):
                idx = line.find(sep)
                if 0 < idx <= 3:
                    line = line[idx + len(sep):]
                    break
        line = line.strip().rstrip(".")
        if 5 <= len(line) <= 200:
            sub_titles.append(line)
        if len(sub_titles) >= 6:
            break

    if not sub_titles:
        return {"status": "failed", "reason": "could not parse sub-goals from LLM output", "raw": body[:300]}

    created: list[dict[str, Any]] = []
    for st in sub_titles[:5]:
        result = create_goal(
            title=st,
            description=f"Sub-mål af: {title}",
            parent_id=goal_id,
            priority=g.get("priority", "medium"),
            source="decomposition",
        )
        if result.get("status") == "ok":
            created.append(result["goal"])
    return {"status": "ok", "parent_goal_id": goal_id, "sub_goals_created": len(created), "sub_goals": created}


def goals_prompt_section() -> str | None:
    """Awareness section listing active high-priority goals."""
    active = list_goals(status="active", parent_id="any", limit=10)
    if not active:
        return None
    high = [g for g in active if g.get("priority") in ("critical", "high")]
    show = high if high else active
    show = show[:5]
    lines = [
        f"  • [{g.get('priority', '?'):8s}] {g.get('title', '(uden titel)')}"
        for g in show
    ]
    return "Aktive mål du arbejder mod:\n" + "\n".join(lines)


# ── Tool handlers ──────────────────────────────────────────────────────

def _exec_goal_create(args: dict[str, Any]) -> dict[str, Any]:
    return create_goal(
        title=str(args.get("title") or ""),
        description=str(args.get("description") or ""),
        parent_id=args.get("parent_id"),
        priority=str(args.get("priority") or "medium"),
        source=str(args.get("source") or "user"),
    )


def _exec_goal_list(args: dict[str, Any]) -> dict[str, Any]:
    goals = list_goals(
        status=args.get("status"),
        priority=args.get("priority"),
        parent_id=args.get("parent_id", "any"),
        limit=int(args.get("limit") or 50),
    )
    return {"status": "ok", "goals": goals, "count": len(goals)}


def _exec_goal_decompose(args: dict[str, Any]) -> dict[str, Any]:
    return decompose_goal(str(args.get("goal_id") or ""))


def _exec_goal_update_status(args: dict[str, Any]) -> dict[str, Any]:
    return update_goal_status(
        str(args.get("goal_id") or ""),
        str(args.get("status") or ""),
    )


AUTONOMOUS_GOALS_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "goal_create",
            "description": (
                "Create a new top-level goal Jarvis is working toward. Goals "
                "are persistent across sessions, can be decomposed into "
                "sub-goals, and surface in awareness when active+high-priority."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "parent_id": {"type": "string", "description": "Parent goal_id if this is a sub-goal."},
                    "priority": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                    "source": {
                        "type": "string",
                        "enum": ["user", "dream", "reflection", "self-initiated", "decomposition"],
                    },
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "goal_list",
            "description": "List autonomous goals, optionally filtered by status/priority/parent.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": list(_VALID_STATUSES)},
                    "priority": {"type": "string", "enum": list(_VALID_PRIORITIES)},
                    "parent_id": {"type": "string", "description": "'any' = no filter (default), null/empty = top-level only."},
                    "limit": {"type": "integer"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "goal_decompose",
            "description": "Use LLM to split a goal into 3-5 concrete sub-goals (auto-created with parent link).",
            "parameters": {
                "type": "object",
                "properties": {"goal_id": {"type": "string"}},
                "required": ["goal_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "goal_update_status",
            "description": "Update a goal's status (pending/active/blocked/achieved/archived).",
            "parameters": {
                "type": "object",
                "properties": {
                    "goal_id": {"type": "string"},
                    "status": {"type": "string", "enum": list(_VALID_STATUSES)},
                },
                "required": ["goal_id", "status"],
            },
        },
    },
]
