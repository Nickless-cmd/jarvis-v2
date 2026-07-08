"""Cowork-dashboard routes. Tynde — al opsamling sker i core.services.cowork_feed,
og BLOKERENDE arbejde offloades til asyncio.to_thread (jarvis-api --workers 1, så
ét blokerende kald fryser hele API'et — se reference_async_blocking_worker)."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Body, HTTPException

from core.services import cowork_feed

router = APIRouter(prefix="/cowork", tags=["cowork"])


def _role_owner() -> tuple[bool, str | None]:
    """(is_owner, user_id) for den indloggede bruger. Owner afgøres af bruger-
    rollen (find_user_by_discord_id().role == "owner"), IKKE en streng-sammenligning
    — Bjørns user_id er hans Discord-ID, ikke "owner". Ubundet (no-auth) = owner."""
    from core.identity.workspace_context import current_user_id
    uid = current_user_id() or None
    if uid is None:
        return True, None
    try:
        from core.identity.users import find_user_by_discord_id
        u = find_user_by_discord_id(str(uid))
        return (getattr(u, "role", "") == "owner"), uid
    except Exception:
        return False, uid


def _resolve_item(item_id: str, decision: str) -> dict:
    """Router en godkendelses-beslutning til den rette eksisterende resolver.
    decision: "approve" | "reject". Prøver initiative-queue først, så capability-
    approval. BLOKERENDE — kaldes via to_thread."""
    approved = decision == "approve"
    # Autonomy-proposals (prop-xxxxxx): commits/planer/prompt-ændringer.
    try:
        from core.services.autonomy_proposal_queue import approve_proposal, reject_proposal
        res = approve_proposal(item_id) if approved else reject_proposal(item_id)
        if res and str(res.get("status") or "") not in ("not-found", ""):
            return {"status": "ok", "decision": decision, "via": "proposal"}
    except Exception:
        pass
    try:
        from core.services.initiative_queue import approve_initiative, reject_initiative
        res = approve_initiative(item_id) if approved else reject_initiative(item_id)
        if res:
            return {"status": "ok", "decision": decision, "via": "initiative"}
    except Exception:
        pass
    try:
        from core.services.visible_runs import resolve_pending_approval
        res = resolve_pending_approval(item_id, approved=approved)
        if res is not None:
            return {"status": "ok", "decision": decision, "via": "capability"}
    except Exception:
        pass
    return {"status": "error", "reason": "unknown_item", "id": item_id}


@router.get("/queue")
async def cowork_queue() -> dict:
    """Godkendelses-kø for den indloggede bruger (owner ser alt). Bygges via
    cowork_feed.build_queue i to_thread. Returnerer {"items": [...]}."""
    is_owner, uid = _role_owner()
    items = await asyncio.to_thread(cowork_feed.build_queue, user_id=uid, is_owner=is_owner)
    return {"items": items}


@router.get("/plans")
async def cowork_plans() -> dict:
    """Planer for den indloggede bruger (owner ser alt) via cowork_feed.list_plans
    i to_thread. Returnerer {"plans": [...]}."""
    is_owner, uid = _role_owner()
    plans = await asyncio.to_thread(cowork_feed.list_plans, user_id=uid, is_owner=is_owner)
    return {"plans": plans}


@router.get("/todos")
async def cowork_todos() -> dict:
    """Todo-feed for den indloggede bruger (owner ser alt) via
    cowork_feed.list_todos_feed i to_thread. Returnerer {"todos": [...]}."""
    is_owner, uid = _role_owner()
    todos = await asyncio.to_thread(cowork_feed.list_todos_feed, user_id=uid, is_owner=is_owner)
    return {"todos": todos}


_VALID_TODO_STATUSES = ("pending", "in_progress", "completed", "paused")


@router.post("/todos")
async def cowork_create_todo(payload: dict = Body(default={})) -> dict:
    """Opret en cowork-todo fra payload["content"]. Owner-only (403 ellers);
    tom content → error. Kalder add_cowork_todo i to_thread."""
    is_owner, _uid = _role_owner()
    if not is_owner:
        raise HTTPException(status_code=403, detail="todos er kun for owner")
    content = str((payload or {}).get("content") or "").strip()
    if not content:
        return {"status": "error", "error": "content er påkrævet"}
    from core.services.agent_todos import add_cowork_todo
    return await asyncio.to_thread(add_cowork_todo, content)


@router.post("/todos/{todo_id}/status")
async def cowork_set_todo_status(todo_id: str, payload: dict = Body(default={})) -> dict:
    """Sæt status på en todo. Owner-only (403 ellers); status skal være en af
    _VALID_TODO_STATUSES ellers error. Kalder update_todo_status_anywhere i to_thread."""
    is_owner, _uid = _role_owner()
    if not is_owner:
        raise HTTPException(status_code=403, detail="todos er kun for owner")
    status = str((payload or {}).get("status") or "").strip().lower()
    if status not in _VALID_TODO_STATUSES:
        return {"status": "error", "error": f"status skal være en af {_VALID_TODO_STATUSES}"}
    from core.services.agent_todos import update_todo_status_anywhere
    return await asyncio.to_thread(update_todo_status_anywhere, todo_id, status)


@router.delete("/todos/{todo_id}")
async def cowork_delete_todo(todo_id: str) -> dict:
    """Slet en todo. Owner-only (403 ellers). Kalder remove_todo_anywhere i to_thread."""
    is_owner, _uid = _role_owner()
    if not is_owner:
        raise HTTPException(status_code=403, detail="todos er kun for owner")
    from core.services.agent_todos import remove_todo_anywhere
    return await asyncio.to_thread(remove_todo_anywhere, todo_id)


@router.post("/todos/{todo_id}/expiry")
async def cowork_set_todo_expiry(todo_id: str, payload: dict = Body(default={})) -> dict:
    """Sæt (eller ryd) udløbstidspunkt på en todo fra payload["expires_at"] — tom
    værdi rydder. Owner-only (403 ellers). Kalder set_todo_expiry_anywhere i to_thread."""
    is_owner, _uid = _role_owner()
    if not is_owner:
        raise HTTPException(status_code=403, detail="todos er kun for owner")
    raw = (payload or {}).get("expires_at")
    expires_at = str(raw).strip() if raw else None
    from core.services.agent_todos import set_todo_expiry_anywhere
    return await asyncio.to_thread(set_todo_expiry_anywhere, todo_id, expires_at)


@router.get("/channels")
async def cowork_channels() -> dict:
    """Kanal-status via cowork_feed.channel_status i to_thread. Owner-only (403
    ellers). Returnerer {"channels": [...]}."""
    is_owner, _uid = _role_owner()
    if not is_owner:
        raise HTTPException(status_code=403, detail="kanaler er kun for owner")
    chans = await asyncio.to_thread(cowork_feed.channel_status)
    return {"channels": chans}


@router.get("/agents")
async def cowork_agents() -> dict:
    """Aktive dispatch-agenter (§19.5 command center). Owner-only."""
    is_owner, _uid = _role_owner()
    if not is_owner:
        raise HTTPException(status_code=403, detail="agenter er kun for owner")
    agents = await asyncio.to_thread(cowork_feed.list_active_agents)
    return {"agents": agents}


@router.post("/queue/{item_id}/approve")
async def cowork_approve(item_id: str) -> dict:
    """Godkend et kø-item (proposal/initiative/capability) via _resolve_item i to_thread."""
    return await asyncio.to_thread(_resolve_item, item_id, "approve")


@router.post("/queue/{item_id}/reject")
async def cowork_reject(item_id: str) -> dict:
    """Afvis et kø-item (proposal/initiative/capability) via _resolve_item i to_thread."""
    return await asyncio.to_thread(_resolve_item, item_id, "reject")


# ── Cross-user share-guard (§4.4, Fase 6 #1) ────────────────────────────────
# Pending "privat eller del?"-beslutninger. Privatlivs-følsomt → kun owner.

@router.get("/share-guard")
async def cowork_share_guard() -> dict:
    """Ventende "privat eller del?"-beslutninger via share_guard_store.list_pending
    i to_thread. Owner-only (403 ellers, privatlivs-følsomt). Returnerer {"pending": [...]}."""
    is_owner, _uid = _role_owner()
    if not is_owner:
        raise HTTPException(status_code=403, detail="share-guard er kun for owner")
    from core.services.share_guard_store import list_pending
    items = await asyncio.to_thread(list_pending)
    return {"pending": items}


@router.post("/share-guard/{decision_id}/resolve")
async def cowork_share_guard_resolve(decision_id: str, shared: bool) -> dict:
    """Afgør en share-beslutning. shared=true → okay at dele; false → hold privat."""
    is_owner, _uid = _role_owner()
    if not is_owner:
        raise HTTPException(status_code=403, detail="share-guard er kun for owner")
    from core.services.share_guard_store import resolve as _resolve
    ok = await asyncio.to_thread(_resolve, decision_id, shared=shared)
    if not ok:
        raise HTTPException(status_code=404, detail="ukendt beslutning")
    return {"status": "ok", "decision_id": decision_id, "shared": shared}


# ── UI-panel-kald (§8.2, Fase 6 #3) ─────────────────────────────────────────
# Jarvis beder desk-appen om at åbne et panel; desk poller her + åbner + ack'er.

@router.get("/ui-panel/pending")
async def cowork_ui_panel_pending() -> dict:
    """Ventende UI-panel-åbnings-kald via ui_panel_store.list_pending i to_thread;
    desk poller her. Returnerer {"pending": [...]}."""
    from core.services.ui_panel_store import list_pending
    items = await asyncio.to_thread(list_pending)
    return {"pending": items}


@router.post("/ui-panel/{request_id}/ack")
async def cowork_ui_panel_ack(request_id: str) -> dict:
    """Kvittér et UI-panel-kald som håndteret via ui_panel_store.ack i to_thread.
    Returnerer {"status": "ok"|"unknown", "request_id": ...}."""
    from core.services.ui_panel_store import ack
    ok = await asyncio.to_thread(ack, request_id)
    return {"status": "ok" if ok else "unknown", "request_id": request_id}


# ── Runtime→app instruktioner (§18.5 Fase 2) ──────────────────────────────
# Jarvis beder appen handle på brugerens enhed (send besked via kanal-plugin,
# vis notifikation, send rapport); desk poller her, udfører lokalt + ack'er.

@router.get("/app-dispatch/pending")
async def cowork_app_dispatch_pending() -> dict:
    """Ventende runtime→app-instruktioner via app_dispatch_store.list_pending i
    to_thread; desk poller her og udfører lokalt. Returnerer {"pending": [...]}."""
    from core.services.app_dispatch_store import list_pending
    items = await asyncio.to_thread(list_pending)
    return {"pending": items}


@router.post("/app-dispatch/{dispatch_id}/ack")
async def cowork_app_dispatch_ack(dispatch_id: str) -> dict:
    """Kvittér en app-dispatch som udført via app_dispatch_store.ack i to_thread.
    Returnerer {"status": "ok"|"unknown", "dispatch_id": ...}."""
    from core.services.app_dispatch_store import ack
    ok = await asyncio.to_thread(ack, dispatch_id)
    return {"status": "ok" if ok else "unknown", "dispatch_id": dispatch_id}
