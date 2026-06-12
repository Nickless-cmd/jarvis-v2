from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from core.services.chat_sessions import (
    append_chat_message,
    create_chat_session,
    delete_chat_session,
    get_chat_session,
    list_chat_sessions,
    rename_chat_session,
)
from core.services.visible_runs import (
    cancel_visible_run,
    resolve_pending_approval,
    start_visible_run,
)

router = APIRouter(prefix="/chat", tags=["chat"])

# ── Preview-panel: path-jailed fil-læsning (jarvis-desk) ──
_FILE_ROOTS = ("docs", "workspace", "core", "apps", "scripts")
_LANG_BY_EXT = {
    ".py": "python", ".ts": "typescript", ".tsx": "tsx", ".js": "javascript",
    ".json": "json", ".md": "markdown", ".css": "css", ".sh": "bash", ".txt": "text",
}


def _repo_root() -> Path:
    # chat.py: apps/api/jarvis_api/routes/ → fire niveauer op til repo-rod.
    return Path(__file__).resolve().parents[4]


@router.get("/file")
async def chat_read_file(path: str = Query(...)) -> dict:
    """Læs en repo-fil til preview-panelet. Path-jail: kun whitelisted rødder."""
    root = _repo_root()
    candidate = (root / path).resolve()
    try:
        rel = candidate.relative_to(root)
    except ValueError:
        raise HTTPException(status_code=403, detail="uden for jail")
    if not rel.parts or rel.parts[0] not in _FILE_ROOTS:
        raise HTTPException(status_code=403, detail="ikke-whitelisted rod")
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="ikke fundet")
    content = candidate.read_text(encoding="utf-8", errors="replace")
    return {"path": path, "content": content, "language": _LANG_BY_EXT.get(candidate.suffix, "text")}


class ChatStreamRequest(BaseModel):
    message: str = ""
    session_id: str = ""
    attachment_ids: list[str] = []
    approval_mode: str = "ask"  # "ask" | "trust"
    # Thinking mode for reasoning-capable models (deepseek-v4-flash et al.).
    # "fast" = no thinking (intuitive answer)
    # "think" = default thinking (balanced)
    # "deep" = max reasoning effort (slowest, hardest problems)
    # Ignored for models that don't support thinking parameters.
    thinking_mode: str = "think"
    # UI-mode: "chat" begrænser værktøjer til en samtale-allowlist; "code"
    # låser kode-tools op (tool_scope="code"). "" = ubegrænset (rolle-filter
    # gælder stadig). Sættes af jarvis-desk pr. mode.
    mode: str = ""
    # Code-mode workspace (hvor Jarvis' fil-tools arbejder).
    workspace_kind: str = ""   # "container" | "workstation" | ""
    workspace_root: str = ""


class ChatSessionCreateRequest(BaseModel):
    title: str = "New chat"
    workspace_kind: str = ""   # "container" | "workstation" | "" (Code mode)
    workspace_root: str = ""


class ChatSessionRenameRequest(BaseModel):
    title: str


@router.get("/sessions")
async def chat_sessions() -> dict:
    """List chat sessions.

    When the request carries an X-JarvisX-User header (set by the
    JarvisX desktop app), only sessions that user has actually
    participated in are returned — this is what keeps Bjørn's and
    Mikkel's chat histories from bleeding into each other in the
    sidebar. Webchat without the header returns the unfiltered list,
    same as before.
    """
    from core.identity.workspace_context import current_user_id
    uid = current_user_id() or None
    return {"items": list_chat_sessions(user_id=uid)}


# Bemærk: defineres FØR /sessions/{session_id} så "search" ikke fanges som id.
@router.get("/sessions/search")
async def chat_search_sessions(q: str = "", limit: int = 30) -> dict:
    """Søg sessioner på titel + besked-indhold. Scopes pr. bruger som
    /sessions. Returnerer {items: [{session_id, title, snippet, updated_at}]}."""
    from core.identity.workspace_context import current_user_id
    from core.services.chat_sessions import search_chat_sessions
    uid = current_user_id() or None
    return {"items": search_chat_sessions(q, user_id=uid, limit=limit)}


@router.get("/active-runs")
async def chat_active_runs() -> dict:
    """Sessioner med et aktivt visible-run lige nu (#8 — autonome/baggrunds-runs).

    Bruges af Sidebar til at vise en arbejds-indikator på en session der ikke er
    fremme. Højst ét aktivt visible-run ad gangen. Friskheds-guard mod phantom-
    state (et run der døde uden at rydde op): kun med hvis < 10 min gammelt og
    ikke cancelled."""
    from datetime import UTC, datetime
    from core.services.visible_runs import _get_active_visible_run_state
    out: list[str] = []
    try:
        state = _get_active_visible_run_state() or {}
        sid = str(state.get("session_id") or "").strip()
        if sid and not state.get("cancelled"):
            started = str(state.get("started_at") or "")
            fresh = True
            if started:
                try:
                    age = (datetime.now(UTC) - datetime.fromisoformat(started)).total_seconds()
                    fresh = age < 600
                except (ValueError, TypeError):
                    fresh = True
            if fresh:
                out.append(sid)
    except Exception:
        pass
    return {"session_ids": out}


@router.get("/context-info")
async def chat_context_info() -> dict:
    """Kontekst-tærskler til composer-ringen (#9). Kun ægte config-tal:
    autocompact-punktet (context_compact_threshold_tokens). Klienten holder
    selv tælleren (usage.input + cache fra streamen)."""
    from core.runtime.settings import load_settings
    s = load_settings()
    return {
        "compact_at": int(s.context_compact_threshold_tokens or 0),
        "run_compact_at": int(s.context_run_compact_threshold_tokens or 0),
    }


@router.post("/sessions")
async def chat_create_session(request: ChatSessionCreateRequest) -> dict:
    return {"session": create_chat_session(
        title=request.title,
        workspace_kind=request.workspace_kind or None,
        workspace_root=request.workspace_root or None,
    )}


@router.get("/sessions/{session_id}")
async def chat_session(session_id: str) -> dict:
    session = get_chat_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return {"session": session}


@router.put("/sessions/{session_id}/rename")
async def chat_rename_session(session_id: str, request: ChatSessionRenameRequest) -> dict:
    session = rename_chat_session(session_id, title=request.title)
    if session is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return {"session": session}


@router.delete("/sessions/{session_id}")
async def chat_delete_session(session_id: str) -> dict:
    if not delete_chat_session(session_id):
        raise HTTPException(status_code=404, detail="Chat session not found")
    return {"ok": True, "session_id": session_id}


@router.post("/stream")
async def chat_stream(request: ChatStreamRequest) -> StreamingResponse:
    session_id = request.session_id.strip()
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id must be a non-empty string")
    if get_chat_session(session_id) is None:
        raise HTTPException(status_code=404, detail="Chat session not found")
    print(
        f"[chat/stream] session={session_id[:20]} "
        f"attachment_ids={list(request.attachment_ids or [])} "
        f"message_len={len(request.message)}",
        flush=True,
    )

    # Prepend attachment-direktiv-blok (delt helper — bruges også af v2) så Jarvis
    # ved HVORDAN han ser filen (analyze_image med eksakt sti).
    from apps.api.jarvis_api.routes.attachments import apply_attachment_context
    effective_message = apply_attachment_context(request.message, request.attachment_ids)

    # Reject empty / whitespace-only messages cleanly (400) instead of
    # letting append_chat_message raise a ValueError that becomes a 500.
    # JarvisX UI occasionally sends empty payloads (e.g. accidental enter-
    # press) and we don't want that to look like a server crash.
    if not (effective_message or "").strip():
        raise HTTPException(
            status_code=400,
            detail="message must not be empty or whitespace-only",
        )

    # Stamp user_id from workspace context (resolved by jarvisx_user_routing
    # middleware from the Bearer token's `sub` claim). Without this the
    # message is anonymized in storage → prompt_contract's multi-user
    # speaker prefix can't label it → Jarvis falls back to assuming it's
    # the owner (Bjørn) regardless of who actually typed it.
    from core.identity.workspace_context import current_user_id
    _uid = current_user_id() or None
    append_chat_message(
        session_id=session_id,
        role="user",
        content=effective_message,
        user_id=_uid,
    )
    from core.services.notification_bridge import pin_session
    pin_session(session_id)
    return StreamingResponse(
        start_visible_run(
            message=effective_message,
            session_id=session_id,
            approval_mode=request.approval_mode,
            thinking_mode=request.thinking_mode,
            # Pass current user_id explicitly. The streaming generator
            # body runs AFTER the middleware has reset workspace_context
            # (call_next returns the response object before the body
            # streams), so the generator must rebind context itself.
            # Without this, operator_* tools dispatch to owner via
            # _operator_user_id fallback. See 2026-05-28 bug investigation.
            force_user_id=_uid,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.post("/approvals/{approval_id}/approve")
async def chat_approve_tool(approval_id: str) -> dict:
    # CRITICAL: must run in a thread, not on the event loop directly.
    # resolve_pending_approval → execute_tool_force → _run_operator_async
    # uses asyncio.run_coroutine_threadsafe(coro, main_loop) + cf_fut.result()
    # which deadlocks if called from main_loop itself (loop blocked → coroutine
    # can't run → future never resolves → 60s timeout → tool returns error
    # AND THEN the coroutine finally runs after the deadlock returns).
    # Observed live 2026-05-28: operator_bash "echo hej" returned timeout-error
    # ~60s after user clicked Approve, even though the bridge replied in 20ms.
    import asyncio
    result = await asyncio.to_thread(resolve_pending_approval, approval_id, approved=True)
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result.get("error", "Not found"))
    return result


@router.post("/approvals/{approval_id}/deny")
async def chat_deny_tool(approval_id: str) -> dict:
    # Same deadlock-avoidance as /approve: see comment there. Deny doesn't
    # actually run the tool, but resolve_pending_approval is sync either way
    # and consistency keeps the codepath simple.
    import asyncio
    result = await asyncio.to_thread(resolve_pending_approval, approval_id, approved=False)
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result.get("error", "Not found"))
    return result


@router.post("/runs/{run_id}/cancel")
async def chat_cancel_run(run_id: str) -> dict:
    if not cancel_visible_run(run_id):
        raise HTTPException(status_code=404, detail="Visible run not active")
    return {
        "ok": True,
        "run_id": run_id,
        "status": "cancelled",
    }


@router.post("/runs/{run_id}/steer")
async def chat_steer_run(run_id: str, body: dict) -> dict:
    """Mid-flight steer: inject a user message into a running visible-run.
    The agentic loop picks it up at the next round boundary."""
    from core.services.visible_runs import append_visible_run_steer
    content = str((body or {}).get("content") or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="content required")
    ok = append_visible_run_steer(run_id, content)
    if not ok:
        raise HTTPException(status_code=404, detail="Visible run not active")
    return {"ok": True, "run_id": run_id, "queued": True}
