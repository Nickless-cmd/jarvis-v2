"""Cowork-dashboard routes. Tynde — al opsamling sker i core.services.cowork_feed,
og BLOKERENDE arbejde offloades til asyncio.to_thread (jarvis-api --workers 1, så
ét blokerende kald fryser hele API'et — se reference_async_blocking_worker)."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

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


# ── Cross-user share-guard (§4.4, Fase 6 #1) ────────────────────────────────
# Pending "privat eller del?"-beslutninger. Privatlivs-følsomt → kun owner.

@router.get("/share-guard")
async def cowork_share_guard() -> dict:
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
    from core.services.ui_panel_store import list_pending
    items = await asyncio.to_thread(list_pending)
    return {"pending": items}


@router.post("/ui-panel/{request_id}/ack")
async def cowork_ui_panel_ack(request_id: str) -> dict:
    from core.services.ui_panel_store import ack
    ok = await asyncio.to_thread(ack, request_id)
    return {"status": "ok" if ok else "unknown", "request_id": request_id}
