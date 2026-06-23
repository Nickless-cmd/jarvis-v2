"""Real-time Central-vindue til owner (jarvis-desk code mode).

Owner-only: Centralen er kontrol-/observabilitets-planen — kun ejeren følger nervesystemet
live. Tynd route; det blokerende arbejde (DB-læsninger) kører via asyncio.to_thread så
--workers 1-API'et ikke fryser. Snapshot polles af desk-panelet (~1-2s).
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/central", tags=["central"])


def _require_owner() -> None:
    from core.identity.workspace_context import current_user_id
    uid = current_user_id() or None
    if uid is None:
        return  # ubundet (no-auth) = owner
    try:
        from core.identity.users import find_user_by_discord_id
        if getattr(find_user_by_discord_id(str(uid)), "role", "") == "owner":
            return
    except Exception:
        pass
    raise HTTPException(status_code=403, detail="Centralen er kun for owner")


@router.get("/realtime")
async def central_realtime() -> dict:
    """Ét snapshot af Centralens live-tilstand (puls/feed/flag/læring)."""
    _require_owner()
    from core.services.central_realtime import realtime_snapshot
    return await asyncio.to_thread(realtime_snapshot)


@router.post("/nerve/{nerve}/toggle")
async def central_nerve_toggle(nerve: str, enabled: bool = True) -> dict:
    """Owner kill-switch: tænd/sluk en nerve LIVE (Lag 5). Sikkerheds-nerver kan IKKE
    slås fra (central_switches håndhæver det) — så returneres den uændrede tilstand."""
    _require_owner()

    def _toggle() -> dict:
        try:
            from core.services import central_switches
            res = central_switches.set_enabled("nerve", str(nerve), bool(enabled))
            return {"ok": True, "nerve": str(nerve), "result": res}
        except Exception as exc:
            return {"ok": False, "nerve": str(nerve), "error": f"{type(exc).__name__}: {exc}"}

    return await asyncio.to_thread(_toggle)
