"""JarvisX chat-session support route group.

Preferences, tool inventory, todos, chat search, staged edits, stored
tool-result bodies, plan proposals, and session forking. Extracted from
routes/jarvisx.py.

Behavior-preserving: pure code movement, no logic changes.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from apps.api.jarvis_api.routes.jarvisx_common import _require_owner, logger

router = APIRouter(prefix="/api", tags=["jarvisx"])


@router.get("/preferences")
def preferences_get() -> dict[str, Any]:
    """User-level UI preferences (output style, tool permissions, etc).

    Stored in JARVIS_HOME/config/jarvisx_prefs.json so they survive
    runtime restarts and apply across sessions.
    """
    from core.runtime.config import CONFIG_DIR
    p = Path(CONFIG_DIR) / "jarvisx_prefs.json"
    if not p.is_file():
        return {"output_style": "balanced", "tool_permissions": {}}
    import json as _json
    try:
        data = _json.loads(p.read_text(encoding="utf-8"))
        return {
            "output_style": str(data.get("output_style") or "balanced"),
            "tool_permissions": data.get("tool_permissions") if isinstance(data.get("tool_permissions"), dict) else {},
        }
    except Exception:
        return {"output_style": "balanced", "tool_permissions": {}}


class PreferencesUpdate(BaseModel):
    output_style: str | None = None
    tool_permissions: dict[str, str] | None = None


@router.post("/preferences")
def preferences_set(payload: PreferencesUpdate) -> dict[str, Any]:
    from core.runtime.config import CONFIG_DIR
    import json as _json
    p = Path(CONFIG_DIR) / "jarvisx_prefs.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    current: dict[str, Any] = {}
    if p.is_file():
        try:
            current = _json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            current = {}
    if payload.output_style is not None:
        if payload.output_style in {"concise", "balanced", "detailed", "technical"}:
            current["output_style"] = payload.output_style
    if payload.tool_permissions is not None:
        # Validate values
        valid = {}
        for k, v in payload.tool_permissions.items():
            if v in {"allow", "deny", "ask"}:
                valid[str(k)] = v
        current["tool_permissions"] = valid
    p.write_text(_json.dumps(current, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"status": "ok", "preferences": current}


@router.get("/tools/inventory")
def tools_inventory() -> dict[str, Any]:
    """Return the full tool catalog with name + description + required params.
    Used by the JarvisX 'tool inventory' modal."""
    try:
        from core.tools.simple_tools import TOOL_DEFINITIONS as defs
    except Exception:
        defs = []
    items: list[dict[str, Any]] = []
    for d in defs:
        fn = d.get("function") if isinstance(d, dict) else None
        if not isinstance(fn, dict):
            continue
        name = str(fn.get("name") or "")
        if not name:
            continue
        params = fn.get("parameters") or {}
        required = list(params.get("required", [])) if isinstance(params, dict) else []
        items.append({
            "name": name,
            "description": str(fn.get("description") or "")[:600],
            "required": required,
        })
    items.sort(key=lambda x: x["name"])
    return {"count": len(items), "tools": items}


@router.get("/todos")
def todos_list(session_id: str = Query(..., description="Session id")) -> dict[str, Any]:
    """List todos for a session — used by JarvisX's TodoPanel UI."""
    from core.services.agent_todos import list_todos
    items = list_todos(session_id)
    return {"session_id": session_id, "count": len(items), "todos": items}


class TodoStatusUpdate(BaseModel):
    session_id: str
    todo_id: str
    status: str


@router.post("/todos/status")
def todos_status(payload: TodoStatusUpdate) -> dict[str, Any]:
    from core.services.agent_todos import update_todo_status
    return update_todo_status(payload.session_id, payload.todo_id, payload.status)


@router.get("/chat/search")
def chat_search(
    q: str = Query(..., min_length=1, max_length=200, description="Search query"),
    limit: int = Query(default=60, ge=1, le=300),
    scope: str = Query(default="all", description="all|current_workspace"),
) -> dict[str, Any]:
    """Full-text search across chat_messages.

    Returns hits with their session_id, message snippet, role, time.
    Used by JarvisX's Cmd-K search modal to jump across sessions.

    Default scope=all returns everyone's hits — JarvisX UI typically
    filters to current workspace via the `current_workspace` scope which
    reads the bound workspace from the user-routing middleware.
    """
    from core.runtime.config import JARVIS_HOME
    import sqlite3
    db_path = Path(JARVIS_HOME) / "state" / "jarvis.db"
    if not db_path.is_file():
        return {"hits": [], "count": 0}
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        like = f"%{q}%"
        params: list[Any] = [like]
        clause = "content LIKE ?"
        if scope == "current_workspace":
            from core.identity.workspace_context import current_workspace_name
            ws = current_workspace_name() or "default"
            clause += " AND workspace_name = ?"
            params.append(ws)
        params.append(int(limit))
        rows = conn.execute(
            f"""
            SELECT message_id, session_id, role, content, created_at,
                   user_id, workspace_name
            FROM chat_messages
            WHERE {clause}
            ORDER BY id DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
        # Also pull the session titles so the UI can show context
        session_ids = sorted({r["session_id"] for r in rows})
        title_map: dict[str, str] = {}
        if session_ids:
            placeholders = ",".join("?" * len(session_ids))
            try:
                trows = conn.execute(
                    f"SELECT id, title FROM chat_sessions WHERE id IN ({placeholders})",
                    session_ids,
                ).fetchall()
                for tr in trows:
                    title_map[tr["id"]] = tr["title"]
            except Exception:
                # chat_sessions table layout may differ; fall back silently
                pass
    finally:
        conn.close()

    hits = []
    q_low = q.lower()
    for r in rows:
        content = r["content"] or ""
        # Build a short snippet centered on the match
        idx = content.lower().find(q_low)
        if idx < 0:
            snippet = content[:160]
        else:
            start = max(0, idx - 40)
            end = min(len(content), idx + len(q) + 80)
            snippet = ("…" if start > 0 else "") + content[start:end] + ("…" if end < len(content) else "")
        hits.append({
            "message_id": r["message_id"],
            "session_id": r["session_id"],
            "session_title": title_map.get(r["session_id"], ""),
            "role": r["role"],
            "snippet": snippet,
            "created_at": r["created_at"],
            "user_id": r["user_id"],
            "workspace_name": r["workspace_name"],
        })
    return {"q": q, "scope": scope, "count": len(hits), "hits": hits}


@router.get("/staged-edits")
def staged_edits(session_id: str = Query(..., description="Chat session id")) -> dict[str, Any]:
    """List staged edits for a session, including full diffs.

    Used by JarvisX's StagedEditsStrip + diff panel to show what's
    pending without round-tripping through Jarvis.
    """
    from core.services.staged_edits import list_staged
    return list_staged(session_id, full_diffs=True)


@router.post("/staged-edits/commit")
def staged_edits_commit(
    session_id: str = Query(...),
    stage_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Apply staged edits. Same as the commit_staged_edits tool, but
    callable from the UI without going through Jarvis."""
    from core.services.staged_edits import commit_staged
    return commit_staged(session_id, stage_ids=stage_ids)


@router.post("/staged-edits/discard")
def staged_edits_discard(
    session_id: str = Query(...),
    stage_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Drop staged edits without applying."""
    from core.services.staged_edits import discard_staged
    return discard_staged(session_id, stage_ids=stage_ids)


@router.get("/tool-result/{result_id}")
def get_tool_result(result_id: str) -> dict[str, Any]:
    """Fetch the full body of a stored tool_result.

    Used by JarvisX's inline expand-card on `[tool_result:...]` refs in
    chat. Returns the raw stored payload so the UI can detect kind
    (edit_file → diff, bash → terminal, read_file → syntax-highlighted)
    and render accordingly.
    """
    from core.runtime.config import TOOL_RESULTS_DIR
    safe_id = result_id.strip()
    if not safe_id.replace("-", "").replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="invalid result_id")
    p = (TOOL_RESULTS_DIR / f"{safe_id}.json").resolve()
    try:
        p.relative_to(Path(TOOL_RESULTS_DIR).resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="path escape")
    if not p.is_file():
        raise HTTPException(status_code=404, detail="result not found")
    import json as _json
    try:
        data = _json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"parse failed: {exc}")
    return data


# ── Plan proposals (interactive plan-mode) ────────────────────────
# When Jarvis enters plan-mode he writes a structured proposal via the
# propose_plan tool instead of executing. These endpoints let JarvisX
# surface those proposals as interactive cards (approve/dismiss buttons)
# rather than the user having to type the approval into chat.


@router.get("/plans")
def list_plans(
    session_id: str = Query(..., description="Chat session id"),
    include_resolved: bool = Query(default=False),
) -> dict[str, Any]:
    """Pending plan proposals for a session (optionally including resolved)."""
    from core.services.plan_proposals import list_session_plans
    plans = list_session_plans(session_id)
    if not include_resolved:
        plans = [p for p in plans if p.get("status") == "awaiting_approval"]
    return {"session_id": session_id, "count": len(plans), "plans": plans}


@router.post("/plans/{plan_id}/approve")
def approve_plan(plan_id: str) -> dict[str, Any]:
    """Mark a plan as approved. Owner-only."""
    _require_owner()
    from core.services.plan_proposals import resolve_plan
    out = resolve_plan(plan_id, decision="approved")
    if out.get("status") == "error":
        raise HTTPException(status_code=404, detail=out.get("error") or "plan not found")
    return out


@router.post("/plans/{plan_id}/dismiss")
def dismiss_plan(plan_id: str) -> dict[str, Any]:
    """Mark a plan as dismissed. Owner-only."""
    _require_owner()
    from core.services.plan_proposals import resolve_plan
    out = resolve_plan(plan_id, decision="dismissed")
    if out.get("status") == "error":
        raise HTTPException(status_code=404, detail=out.get("error") or "plan not found")
    return out


# ── Session forking ───────────────────────────────────────────────
# "Fork from here" = create a new session with a copy of all messages
# up to and including a given message_id. Useful for exploring a
# different direction without losing the original conversation.


class _ForkPayload(BaseModel):
    source_session_id: str
    up_to_message_id: str
    title: str | None = None


@router.post("/sessions/fork")
def fork_session(payload: _ForkPayload) -> dict[str, Any]:
    """Clone a session up to a specific message_id.

    Copies user/assistant/tool/compact_marker messages in order until
    we've copied the target message_id (inclusive), then stops. The new
    session has its own id; the original is untouched.
    """
    from core.services.chat_sessions import (
        get_chat_session,
        create_chat_session,
        append_chat_message,
    )
    src = get_chat_session(payload.source_session_id)
    if src is None:
        raise HTTPException(status_code=404, detail="source session not found")
    messages = src.get("messages") or []
    if not isinstance(messages, list):
        raise HTTPException(status_code=500, detail="malformed source session")

    # Default title: source title + " (forked)"
    src_title = str(src.get("title") or "Forked chat")
    new_title = (payload.title or f"{src_title} (forked)").strip()[:200] or "Forked chat"
    new_session = create_chat_session(title=new_title)
    new_id = str(new_session.get("id") or "")
    if not new_id:
        raise HTTPException(status_code=500, detail="failed to create session")

    copied = 0
    found_target = False
    for m in messages:
        if not isinstance(m, dict):
            continue
        role = str(m.get("role") or "").strip()
        # Only copy roles append_chat_message accepts; skip approval_request
        # and other UI-side virtual roles.
        if role not in {"user", "assistant", "tool", "compact_marker"}:
            continue
        content = str(m.get("content") or "").strip()
        if not content:
            continue
        try:
            append_chat_message(
                session_id=new_id,
                role=role,
                content=content,
                created_at=str(m.get("created_at") or m.get("ts") or "") or None,
            )
            copied += 1
        except Exception as exc:
            logger.warning("fork: skip message: %s", exc)
        if str(m.get("message_id") or m.get("id") or "") == payload.up_to_message_id:
            found_target = True
            break

    if not found_target:
        # Couldn't find the target message — clean up empty session?
        # Leave it; the user got *some* fork and can decide.
        logger.info(
            "fork: target message %s not found; copied %d messages",
            payload.up_to_message_id, copied,
        )

    return {
        "status": "ok",
        "new_session_id": new_id,
        "title": new_title,
        "messages_copied": copied,
        "found_target": found_target,
    }
