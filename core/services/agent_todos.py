"""Per-session todo tracker — Jarvis' working memory for "what am I doing right now".

Mirrors Claude Code's TodoWrite: a flat list per session, with the rule that
at most ONE item is in_progress at any time. The list is persisted via
state_store and surfaced in every visible prompt so the model can never
lose track of where it is in a multi-step task.

Why per-session: the list IS the conversation thread's plan. Different
sessions are different plans. Cross-session sharing would re-introduce the
"whose task am I working on" confusion the agentic-loop fixes already work
hard to avoid.

Statuses:
- pending       — queued, not yet started
- in_progress   — actively working (max 1 across all todos in a session)
- completed     — done; kept around for the rest of the session as memory
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.runtime.state_store import load_json, save_json

logger = logging.getLogger(__name__)

_STATE_KEY = "agent_todos"
_VALID_STATUSES = ("pending", "in_progress", "completed")


def _load_all() -> dict[str, list[dict[str, Any]]]:
    raw = load_json(_STATE_KEY, {})
    if not isinstance(raw, dict):
        return {}
    out: dict[str, list[dict[str, Any]]] = {}
    for sid, items in raw.items():
        if isinstance(items, list):
            out[str(sid)] = [i for i in items if isinstance(i, dict)]
    return out


def _save_all(data: dict[str, list[dict[str, Any]]]) -> None:
    save_json(_STATE_KEY, data)


def _session_key(session_id: str | None) -> str:
    return str(session_id or "_default")


def list_todos(session_id: str | None) -> list[dict[str, Any]]:
    return list(_load_all().get(_session_key(session_id), []))


def set_todos(session_id: str | None, items: list[dict[str, Any]]) -> dict[str, Any]:
    """Replace the entire todo list for this session.

    Each item may include id (auto-generated if missing), content (required),
    status (default pending). Enforces the ONE in_progress rule by keeping
    only the first in_progress in source order; later ones drop to pending.
    """
    sid = _session_key(session_id)
    cleaned: list[dict[str, Any]] = []
    in_progress_seen = False
    now = datetime.now(UTC).isoformat()
    for raw in items or []:
        if not isinstance(raw, dict):
            continue
        content = str(raw.get("content") or "").strip()
        if not content:
            continue
        status = str(raw.get("status") or "pending").strip().lower()
        if status not in _VALID_STATUSES:
            status = "pending"
        if status == "in_progress":
            if in_progress_seen:
                status = "pending"
            else:
                in_progress_seen = True
        cleaned.append({
            "id": str(raw.get("id") or f"td-{uuid4().hex[:10]}"),
            "content": content[:240],
            "status": status,
            "updated_at": now,
        })
    data = _load_all()
    data[sid] = cleaned
    _save_all(data)
    return {"status": "ok", "session_id": sid, "count": len(cleaned), "todos": cleaned}


def update_todo_status(session_id: str | None, todo_id: str, new_status: str) -> dict[str, Any]:
    sid = _session_key(session_id)
    new_status = (new_status or "").strip().lower()
    if new_status not in _VALID_STATUSES:
        return {"status": "error", "error": f"new_status must be one of {_VALID_STATUSES}"}
    data = _load_all()
    items = data.get(sid, [])
    found = None
    for it in items:
        if it.get("id") == todo_id:
            found = it
            break
    if not found:
        return {"status": "error", "error": f"unknown todo_id {todo_id}"}
    if new_status == "in_progress":
        # Demote any other in_progress to pending — invariant: max 1 active.
        for it in items:
            if it is not found and it.get("status") == "in_progress":
                it["status"] = "pending"
    found["status"] = new_status
    found["updated_at"] = datetime.now(UTC).isoformat()
    data[sid] = items
    _save_all(data)
    return {"status": "ok", "todo": found}


def add_todo(session_id: str | None, content: str) -> dict[str, Any]:
    content = (content or "").strip()
    if not content:
        return {"status": "error", "error": "content is required"}
    sid = _session_key(session_id)
    data = _load_all()
    items = data.get(sid, [])
    item = {
        "id": f"td-{uuid4().hex[:10]}",
        "content": content[:240],
        "status": "pending",
        "updated_at": datetime.now(UTC).isoformat(),
    }
    items.append(item)
    data[sid] = items
    _save_all(data)
    return {"status": "ok", "todo": item, "count": len(items)}


def remove_todo(session_id: str | None, todo_id: str) -> dict[str, Any]:
    sid = _session_key(session_id)
    data = _load_all()
    items = data.get(sid, [])
    before = len(items)
    items = [i for i in items if i.get("id") != todo_id]
    if len(items) == before:
        return {"status": "error", "error": f"unknown todo_id {todo_id}"}
    data[sid] = items
    _save_all(data)
    return {"status": "ok", "removed_id": todo_id, "remaining": len(items)}


def clear_session_todos(session_id: str | None) -> dict[str, Any]:
    sid = _session_key(session_id)
    data = _load_all()
    if sid in data:
        del data[sid]
        _save_all(data)
    return {"status": "ok", "cleared": sid}


def todos_prompt_section(session_id: str | None) -> str | None:
    """Format the active todo list as a prompt block, or None if empty.

    Shows up to 12 items with a status glyph so the model can scan quickly.
    Completed items at the tail give continuity; pending in the middle and
    in_progress at top so the active item is always the first thing seen.
    """
    todos = list_todos(session_id)
    if not todos:
        return None
    glyph = {"in_progress": "▶", "pending": "•", "completed": "✓"}

    def sort_key(it: dict[str, Any]) -> tuple[int, str]:
        order = {"in_progress": 0, "pending": 1, "completed": 2}.get(
            str(it.get("status", "pending")), 1
        )
        return (order, str(it.get("updated_at", "")))

    sorted_items = sorted(todos, key=sort_key)
    lines = []
    for it in sorted_items[:12]:
        s = str(it.get("status", "pending"))
        g = glyph.get(s, "?")
        c = str(it.get("content", "")).strip()
        lines.append(f"{g} {c}")
    header = (
        "Aktive todos for denne session "
        "(max ÉN må være ▶ in_progress ad gangen):"
    )
    return header + "\n" + "\n".join(lines)
