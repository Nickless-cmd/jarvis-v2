"""Push token-registrering. Scoper til den auth'ede bruger."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

import core.services.device_tokens as device_tokens

router = APIRouter(prefix="/push", tags=["push"])


class RegisterBody(BaseModel):
    token: str
    platform: str = "android"


class UnregisterBody(BaseModel):
    token: str


def _current_user() -> str | None:
    from core.identity.workspace_context import current_user_id
    return current_user_id() or None


@router.post("/register")
async def register(body: RegisterBody) -> dict:
    uid = _current_user()
    if not uid or not (body.token or "").strip():
        return {"ok": False}
    device_tokens.register(uid, body.token, body.platform)
    return {"ok": True}


@router.post("/unregister")
async def unregister(body: UnregisterBody) -> dict:
    device_tokens.delete(body.token)
    return {"ok": True}


class WebSubscribeBody(BaseModel):
    endpoint: str
    p256dh: str
    auth: str


@router.get("/web/vapid")
async def web_vapid() -> dict:
    """Den offentlige VAPID-nøgle — klienten skal bruge den til at abonnere.

    Nøglen er offentlig per design (den er den ``applicationServerKey`` browseren
    sender til push-tjenesten); den private ligger i runtime.json.
    """
    from core.services.web_push_gateway import vapid_public_key
    return {"key": vapid_public_key()}


@router.post("/web/subscribe")
async def web_subscribe(body: WebSubscribeBody) -> dict:
    uid = _current_user()
    if not uid or not (body.endpoint or "").strip():
        return {"ok": False}
    from core.services import web_push_subscriptions as subs
    subs.save(uid, body.endpoint, body.p256dh, body.auth)
    return {"ok": True}


@router.post("/web/unsubscribe")
async def web_unsubscribe(body: UnregisterBody) -> dict:
    """Afmeld et web-abonnement. ``token`` bærer her abonnementets endpoint —
    samme form som FCM-afmeldingen, så klienten kan bruge ét kald til begge."""
    from core.services import web_push_subscriptions as subs
    subs.delete(body.token)
    return {"ok": True}
