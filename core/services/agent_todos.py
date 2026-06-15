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

# Stabil session-nøgle for todos oprettet fra cowork-UI'et (ikke en chat-tråd).
COWORK_SESSION = "_cowork"


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

    Phase 1 (2026-05-12): if a todo with plan_id transitions to 'completed',
    notify plan_proposals.mark_step_completed.
    """
    sid = _session_key(session_id)
    cleaned: list[dict[str, Any]] = []
    in_progress_seen = False
    now = datetime.now(UTC).isoformat()

    # Snapshot old state for transition detection
    data = _load_all()
    old_by_id = {str(t.get("id") or ""): t for t in data.get(sid, [])}

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
            "plan_id": raw.get("plan_id"),
            "plan_step_index": raw.get("plan_step_index"),
            "updated_at": now,
        })

    # Capture old plan_ids before replacement — for orphaned-plan detection
    old_plan_ids: set[str] = set()
    for t in data.get(sid, []):
        pid = t.get("plan_id")
        if pid and str(pid).strip():
            old_plan_ids.add(str(pid).strip())

    data[sid] = cleaned
    _save_all(data)

    # Auto-dismiss orphaned plans after full replacement
    _maybe_dismiss_orphaned_plan(sid, old_plan_ids, cleaned)

    # Phase 1 transition detection: pending/in_progress → completed.
    for new_todo in cleaned:
        if new_todo.get("status") != "completed":
            continue
        old = old_by_id.get(str(new_todo.get("id") or ""))
        old_status = (old or {}).get("status")
        if old_status == "completed":
            continue  # already completed — no transition
        pid = new_todo.get("plan_id")
        step_idx = new_todo.get("plan_step_index")
        if pid and step_idx is not None:
            try:
                from core.services.plan_proposals import mark_step_completed
                mark_step_completed(str(pid), int(step_idx))
            except Exception as exc:
                logger.warning(
                    "agent_todos: failed to mark step completed: %s", exc,
                )

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

    old_status = found.get("status")

    if new_status == "in_progress":
        # Demote any other in_progress to pending — invariant: max 1 active.
        for it in items:
            if it is not found and it.get("status") == "in_progress":
                it["status"] = "pending"
    found["status"] = new_status
    found["updated_at"] = datetime.now(UTC).isoformat()
    data[sid] = items
    _save_all(data)

    # Phase 1 transition detection: only fire on actual transition to completed.
    if (
        new_status == "completed"
        and old_status != "completed"
        and found.get("plan_id")
        and found.get("plan_step_index") is not None
    ):
        try:
            from core.services.plan_proposals import mark_step_completed
            mark_step_completed(
                str(found["plan_id"]),
                int(found["plan_step_index"]),
            )
        except Exception as exc:
            logger.warning("agent_todos: failed to mark step completed: %s", exc)

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


def create_from_plan(
    *,
    plan_id: str,
    session_id: str | None,
    steps: list[str],
) -> dict[str, Any]:
    """Append pending todos for each plan step. Idempotent.

    Each todo carries plan_id + plan_step_index so todo completion can
    feed back to plan progress.

    If ANY todo with this plan_id already exists in this session, no-op
    (returns skipped=True). Empty steps list also no-ops.
    """
    pid = str(plan_id or "").strip()
    if not pid:
        return {"status": "error", "error": "plan_id is required"}
    cleaned_steps = [str(s).strip() for s in (steps or []) if str(s).strip()]
    if not cleaned_steps:
        return {"status": "ok", "count": 0, "reason": "empty steps"}

    sid = _session_key(session_id)
    data = _load_all()
    items = list(data.get(sid, []))

    # Idempotency: if any todo with this plan_id exists, skip.
    if any(str(t.get("plan_id") or "") == pid for t in items):
        return {"status": "ok", "skipped": True, "reason": "plan_id already has todos"}

    now = datetime.now(UTC).isoformat()
    new_todos = []
    for idx, content in enumerate(cleaned_steps):
        new_todos.append({
            "id": f"td-{uuid4().hex[:10]}",
            "content": content[:240],
            "status": "pending",
            "plan_id": pid,
            "plan_step_index": idx,
            "updated_at": now,
        })
    items.extend(new_todos)
    data[sid] = items
    _save_all(data)
    return {"status": "ok", "count": len(new_todos), "todos": new_todos}


def _maybe_dismiss_orphaned_plan(
    session_id: str,
    old_plan_ids: set[str],
    new_todos: list[dict[str, Any]],
) -> None:
    """Dismiss any awaiting_approval plan that no longer has linked todos.

    Called after a todo-removal operation.  Scans ``new_todos`` for any
    remaining references to the plan_ids that existed *before* the
    operation.  If a plan_id vanished entirely, and the plan is still
    ``awaiting_approval``, it gets auto-dismissed — the plan no longer
    has anything to execute.
    """
    remaining = set()
    for t in new_todos:
        pid = t.get("plan_id")
        if pid and str(pid).strip():
            remaining.add(str(pid).strip())

    orphaned = old_plan_ids - remaining
    if not orphaned:
        return

    try:
        from core.services.plan_proposals import (
            resolve_plan,
        )

        for pid in orphaned:
            try:
                resolve_plan(pid, decision="dismissed")
                logger.info(
                    "agent_todos: auto-dismissed orphaned plan %s "
                    "(all linked todos removed)",
                    pid,
                )
            except Exception as exc:
                logger.warning(
                    "agent_todos: failed to auto-dismiss plan %s: %s",
                    pid,
                    exc,
                )
    except ImportError:
        pass  # plan_proposals not available — skip gracefully


def remove_todo(session_id: str | None, todo_id: str) -> dict[str, Any]:
    sid = _session_key(session_id)
    data = _load_all()
    items = data.get(sid, [])

    # Capture plan_id before removal
    removed_plan_ids: set[str] = set()
    for i in items:
        if i.get("id") == todo_id:
            pid = i.get("plan_id")
            if pid and str(pid).strip():
                removed_plan_ids.add(str(pid).strip())
            break

    before = len(items)
    items = [i for i in items if i.get("id") != todo_id]
    if len(items) == before:
        return {"status": "error", "error": f"unknown todo_id {todo_id}"}
    data[sid] = items
    _save_all(data)

    _maybe_dismiss_orphaned_plan(sid, removed_plan_ids, items)

    return {"status": "ok", "removed_id": todo_id, "remaining": len(items)}


def add_cowork_todo(content: str) -> dict[str, Any]:
    """Opret en todo i den delte cowork-session (Mission Control UI)."""
    return add_todo(COWORK_SESSION, content)


def _find_session_for_todo(todo_id: str) -> str | None:
    for sid, items in (_load_all() or {}).items():
        if any(str(t.get("id")) == str(todo_id) for t in items):
            return sid
    return None


def update_todo_status_anywhere(todo_id: str, new_status: str) -> dict[str, Any]:
    """Skift status på en todo uanset hvilken session den lever i (cowork kender
    ikke session-nøglen). Genbruger update_todo_status' invarianter."""
    sid = _find_session_for_todo(todo_id)
    if sid is None:
        return {"status": "error", "error": f"unknown todo_id {todo_id}"}
    return update_todo_status(sid, todo_id, new_status)


def remove_todo_anywhere(todo_id: str) -> dict[str, Any]:
    """Slet en todo uanset hvilken session den lever i."""
    sid = _find_session_for_todo(todo_id)
    if sid is None:
        return {"status": "error", "error": f"unknown todo_id {todo_id}"}
    return remove_todo(sid, todo_id)


def clear_session_todos(session_id: str | None) -> dict[str, Any]:
    sid = _session_key(session_id)
    data = _load_all()
    if sid in data:
        old_plan_ids: set[str] = set()
        for t in data[sid]:
            pid = t.get("plan_id")
            if pid and str(pid).strip():
                old_plan_ids.add(str(pid).strip())
        del data[sid]
        _save_all(data)
        _maybe_dismiss_orphaned_plan(sid, old_plan_ids, [])
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


def build_agent_todos_surface() -> dict[str, object]:
    """Mission Control surface — read-only meta-projection.

    Added during 2026-05-13 coverage push. Reports module presence + mode
    so the cartographer registers it as observed. Specific state-readers
    can be added later as the module evolves.
    """
    return {
        "active": True,
        "mode": "agent-todo-tracker",
        "summary": "Module loaded; entry points available.",
        "authority": "derived-read-only",
    }


def _emit_agent_todos_event(kind: str, payload: dict[str, object] | None = None) -> None:
    """Emit a agent_todos-scoped event. Defensive — never blocks caller.

    Cartographer scans for event_bus.publish() text. This wrapper keeps
    publishes consistent across the module.
    """
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            f"agent_todos.{kind}",
            payload or {},
        )
    except Exception:
        pass

