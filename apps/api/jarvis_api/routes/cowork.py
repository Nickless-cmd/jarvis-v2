"""Cowork-dashboard routes. Tynde — al opsamling sker i core.services.cowork_feed,
og BLOKERENDE arbejde offloades til asyncio.to_thread (jarvis-api --workers 1, så
ét blokerende kald fryser hele API'et — se reference_async_blocking_worker)."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from core.services import cowork_feed

router = APIRouter(prefix="/cowork", tags=["cowork"])


def _role_owner() -> tuple[bool, str | None]:
    """(is_owner, user_id) for den indloggede bruger. Tom/owner = owner (samme
    regel som tool_scoping)."""
    from core.identity.workspace_context import current_user_id
    uid = current_user_id() or None
    is_owner = (uid is None) or str(uid) in ("", "owner")
    return is_owner, uid


def _resolve_item(item_id: str, decision: str) -> dict:
    """Router en godkendelses-beslutning til den rette eksisterende resolver.
    decision: "approve" | "reject". Prøver initiative-queue først, så capability-
    approval. BLOKERENDE — kaldes via to_thread."""
    approved = decision == "approve"
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
    is_owner, uid = _role_owner()
    items = await asyncio.to_thread(cowork_feed.build_queue, user_id=uid, is_owner=is_owner)
    return {"items": items}


@router.get("/plans")
async def cowork_plans() -> dict:
    is_owner, uid = _role_owner()
    plans = await asyncio.to_thread(cowork_feed.list_plans, user_id=uid, is_owner=is_owner)
    return {"plans": plans}


@router.get("/todos")
async def cowork_todos() -> dict:
    is_owner, uid = _role_owner()
    todos = await asyncio.to_thread(cowork_feed.list_todos_feed, user_id=uid, is_owner=is_owner)
    return {"todos": todos}


@router.get("/channels")
async def cowork_channels() -> dict:
    is_owner, _uid = _role_owner()
    if not is_owner:
        raise HTTPException(status_code=403, detail="kanaler er kun for owner")
    chans = await asyncio.to_thread(cowork_feed.channel_status)
    return {"channels": chans}


@router.post("/queue/{item_id}/approve")
async def cowork_approve(item_id: str) -> dict:
    return await asyncio.to_thread(_resolve_item, item_id, "approve")


@router.post("/queue/{item_id}/reject")
async def cowork_reject(item_id: str) -> dict:
    return await asyncio.to_thread(_resolve_item, item_id, "reject")
