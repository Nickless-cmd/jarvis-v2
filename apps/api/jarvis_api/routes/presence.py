"""Device-presence + proaktive desktop-notifikationer. Scoper til auth'et bruger."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

import core.services.desktop_notifications as desktop_notifications
import core.services.device_presence as device_presence
import core.services.proactive_router as proactive_router

router = APIRouter(tags=["presence"])


class PingBody(BaseModel):
    device_key: str
    platform: str
    foreground: bool = False
    awake: bool = True
    network: str = "unknown"
    interaction: bool = False


class AckBody(BaseModel):
    notif_id: str


def _current_user() -> str | None:
    from core.identity.workspace_context import current_user_id
    return current_user_id() or None


@router.post("/presence/ping")
async def presence_ping(body: PingBody) -> dict:
    uid = _current_user()
    if not uid or not (body.device_key or "").strip():
        return {"ok": False}
    device_presence.record_ping(
        uid, body.device_key, body.platform,
        foreground=body.foreground, awake=body.awake,
        network=body.network, interaction=body.interaction,
    )
    return {"ok": True}


@router.get("/notifications/pending")
async def notifications_pending() -> dict:
    uid = _current_user()
    if not uid:
        return {"items": []}
    return {"items": desktop_notifications.drain(uid)}


@router.post("/notifications/ack")
async def notifications_ack(body: AckBody) -> dict:
    if (body.notif_id or "").strip():
        proactive_router.ack(body.notif_id)
    return {"ok": True}
