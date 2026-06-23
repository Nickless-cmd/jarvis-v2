"""Real-time Central-vindue til owner (jarvis-desk code mode).

Owner-only: Centralen er kontrol-/observabilitets-planen — kun ejeren følger nervesystemet
live. Tynd route; det blokerende arbejde (DB-læsninger) kører via asyncio.to_thread så
--workers 1-API'et ikke fryser. Snapshot polles af desk-panelet (~1-2s).
"""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/central", tags=["central"])


def _rec_to_item(r) -> dict:
    """TraceRecord → kompakt feed-item (samme form som snapshot-feed'en)."""
    from core.services.central_catalog import is_security_cluster
    cluster = str(getattr(r, "cluster", "") or "")
    sec = False
    try:
        sec = bool(is_security_cluster(cluster))
    except Exception:
        pass
    return {
        "cluster": cluster, "nerve": str(getattr(r, "nerve", "") or ""),
        "kind": str(getattr(r, "kind", "") or ""),
        "decision": str(getattr(r, "decision", "") or ""),
        "reason": str(getattr(r, "reason", "") or "")[:120],
        "run_id": str(getattr(r, "run_id", "") or ""), "security": sec,
    }


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


@router.get("/mind")
async def central_mind(section: str = "") -> dict:
    """Jarvis Mind-hub: Centralen som ÉT samlingspunkt for alt MC viser. Owner-only.

    Uden `section` → index (alle faner + om de er projiceret). Med `section` → den ENE sektions
    projektion (læser den cachede kilde — ingen anden sandhed). Self-safe via central_hub.
    """
    _require_owner()
    from core.services import central_hub
    if section:
        return await asyncio.to_thread(central_hub.mind_section, section)
    return {"index": await asyncio.to_thread(central_hub.mind_index)}


@router.get("/stream")
async def central_stream() -> StreamingResponse:
    """SSE-live-feed af nerve-fyringer (ægte realtid i stedet for 2s-poll). Owner-only.
    Hver fyring → 'data: {feed-item}\\n\\n'. Keepalive-ping hvert 15s. Self-safe."""
    _require_owner()
    from core.services import central_trace

    async def _gen():
        q = central_trace.sink().subscribe()
        try:
            # send de seneste 12 med det samme (panelet har kontekst fra start)
            for r in central_trace.sink().recent(limit=12):
                yield f"data: {json.dumps(_rec_to_item(r))}\n\n"
            while True:
                try:
                    rec = await asyncio.to_thread(q.get, True, 15)
                except Exception:
                    yield ": ping\n\n"  # timeout → keepalive
                    continue
                yield f"data: {json.dumps(_rec_to_item(rec))}\n\n"
        finally:
            central_trace.sink().unsubscribe(q)

    return StreamingResponse(_gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "Connection": "keep-alive"})


@router.get("/nerve/{nerve}")
async def central_nerve_detail(nerve: str) -> dict:
    """Lag 5: én nerves spor + kode-lokation + cluster + live tænd/sluk-tilstand."""
    _require_owner()

    def _detail() -> dict:
        from core.services import central_trace
        from core.services.central_catalog import nerve_location, nerve_cluster, is_security_cluster
        from core.services import central_switches
        recs = [_rec_to_item(r) for r in central_trace.sink().recent(limit=400)
                if str(getattr(r, "nerve", "")) == str(nerve)]
        cluster = ""
        try:
            cluster = nerve_cluster(str(nerve)) or ""
        except Exception:
            pass
        enabled = True
        try:
            enabled = central_switches.is_enabled("nerve", str(nerve))
        except Exception:
            pass
        location = ""
        try:
            location = nerve_location(str(nerve)) or ""
        except Exception:
            pass
        return {
            "nerve": str(nerve), "cluster": cluster,
            "security": bool(is_security_cluster(cluster)) if cluster else False,
            "location": location,
            "enabled": bool(enabled),
            "recent": list(reversed(recs))[:20],   # nyeste først
        }

    return await asyncio.to_thread(_detail)


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
