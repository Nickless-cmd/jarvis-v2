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
