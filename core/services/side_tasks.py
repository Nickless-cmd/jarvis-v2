"""Side-task flag — keep the main thread focused.

When working on task A, Jarvis often notices something tangential that
should be done — but derailing into it costs context and momentum. The
side-task flag lets him capture it without acting: "noted, flagged for
later", and the user (or a future session) can pick it up.

Mirrors my own ``mcp__ccd_session__spawn_task``: short title, longer
self-contained prompt, optional plain-English tldr. Surfaces in the
visible prompt as a small list so the user sees what's queued and can
dismiss anything that's not actually wanted.

Per-session for context, but visible across the workspace so a side
task flagged in Discord is visible in webchat too. Persisted via
state_store.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.runtime.state_store import load_json, save_json

logger = logging.getLogger(__name__)

_STATE_KEY = "side_tasks"
_VALID_STATUSES = ("pending", "dismissed", "activated")
_MAX_SHOWN = 6


def _load_all() -> list[dict[str, Any]]:
    raw = load_json(_STATE_KEY, [])
    if not isinstance(raw, list):
        return []
    return [r for r in raw if isinstance(r, dict)]


def _save_all(items: list[dict[str, Any]]) -> None:
    save_json(_STATE_KEY, items)


def flag(*, title: str, prompt: str, tldr: str = "", session_id: str | None = None) -> dict[str, Any]:
    title = (title or "").strip()
    prompt = (prompt or "").strip()
    if not title or not prompt:
        return {"status": "error", "error": "title and prompt are required"}
    record = {
        "side_task_id": f"side-{uuid4().hex[:10]}",
        "title": title[:120],
        "prompt": prompt[:2000],
        "tldr": tldr[:240] if tldr else "",
        "status": "pending",
        "session_id": str(session_id or "_default"),
        "created_at": datetime.now(UTC).isoformat(),
    }
    items = _load_all()
    items.append(record)
    _save_all(items)
    return {"status": "ok", "side_task_id": record["side_task_id"], "title": title}


def list_pending() -> list[dict[str, Any]]:
    return [r for r in _load_all() if r.get("status") == "pending"]


def resolve(side_task_id: str, *, decision: str) -> dict[str, Any]:
    decision = (decision or "").strip().lower()
    if decision not in {"dismissed", "activated"}:
        return {"status": "error", "error": "decision must be 'dismissed' or 'activated'"}
    items = _load_all()
    found = None
    for r in items:
        if r.get("side_task_id") == side_task_id:
            found = r
            break
    if found is None:
        return {"status": "error", "error": f"unknown side_task_id {side_task_id}"}
    found["status"] = decision
    found["resolved_at"] = datetime.now(UTC).isoformat()
    _save_all(items)
    return {"status": "ok", "side_task_id": side_task_id, "new_status": decision}


def side_tasks_prompt_section() -> str | None:
    pending = list_pending()
    if not pending:
        return None
    pending.sort(key=lambda r: str(r.get("created_at", "")), reverse=True)
    bullets = []
    for r in pending[:_MAX_SHOWN]:
        sid = str(r.get("side_task_id", ""))[-10:]
        title = str(r.get("title", ""))
        tldr = str(r.get("tldr", "")).strip()
        suffix = f" — {tldr}" if tldr else ""
        bullets.append(f"  [{sid}] {title}{suffix}")
    extra = f"  (+{len(pending) - _MAX_SHOWN} mere)" if len(pending) > _MAX_SHOWN else ""
    return (
        "📌 Side-tasks du har flagget til senere "
        "(brug dem hvis brugeren spørger 'hvad mangler?'; ellers ignorer):\n"
        + "\n".join(bullets) + extra
    )


def _exec_flag_side_task(args: dict[str, Any]) -> dict[str, Any]:
    return flag(
        title=str(args.get("title") or ""),
        prompt=str(args.get("prompt") or ""),
        tldr=str(args.get("tldr") or ""),
        session_id=args.get("session_id"),
    )


def _exec_list_side_tasks(_args: dict[str, Any]) -> dict[str, Any]:
    items = list_pending()
    return {"status": "ok", "side_tasks": items, "count": len(items)}


def _exec_dismiss_side_task(args: dict[str, Any]) -> dict[str, Any]:
    return resolve(str(args.get("side_task_id") or ""), decision="dismissed")


def _exec_activate_side_task(args: dict[str, Any]) -> dict[str, Any]:
    return resolve(str(args.get("side_task_id") or ""), decision="activated")


SIDE_TASK_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "flag_side_task",
            "description": (
                "Capture a tangential thing-to-do without derailing the current "
                "task. Use this when you notice something during your main work "
                "that should be addressed, but later. Title is short; prompt is "
                "self-contained instructions for whoever picks it up; tldr is "
                "the human-readable summary. Don't use for things you should "
                "do right now — just for things to do later."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Short imperative phrase, e.g. 'Fix stale README badge'."},
                    "prompt": {"type": "string", "description": "Self-contained instructions; the picker won't have your context."},
                    "tldr": {"type": "string", "description": "Plain-English 1-2 sentence summary for the user."},
                    "session_id": {"type": "string"},
                },
                "required": ["title", "prompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_side_tasks",
            "description": "List pending side-tasks (across all sessions).",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "dismiss_side_task",
            "description": "Drop a flagged side-task — user said no, or it's no longer relevant.",
            "parameters": {
                "type": "object",
                "properties": {"side_task_id": {"type": "string"}},
                "required": ["side_task_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "activate_side_task",
            "description": "Mark a flagged side-task as actively being worked on (no auto-dispatch — just status change).",
            "parameters": {
                "type": "object",
                "properties": {"side_task_id": {"type": "string"}},
                "required": ["side_task_id"],
            },
        },
    },
]
