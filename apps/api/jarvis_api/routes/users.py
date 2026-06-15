"""Owner-only user-administration (spec 2026-06-15 §4/§6). CRUD + GDPR-erasure.

Beskyttet af require_owner (JWT owner-token). Følsomme data dekrypteres kun i
respons (owner ser email/discord); klartekst-password eksponeres aldrig.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from core.identity import user_db
from core.runtime.jarvisx_auth import require_owner

router = APIRouter(prefix="/api/users", tags=["users"])


class PatchUserReq(BaseModel):
    name: str | None = None
    role: str | None = None
    muted: bool | None = None
    tier: str | None = None
    consent_data_processing: bool | None = None
    consent_marketing: bool | None = None
    consent_blind_access: bool | None = None


class DeleteUserReq(BaseModel):
    mode: str = "soft"


@router.get("")
def list_all(claims: dict = Depends(require_owner)) -> JSONResponse:
    return JSONResponse(content={"ok": True, "users": user_db.list_users(include_deleted=True)})


@router.get("/{user_id}")
def get_one(user_id: str, claims: dict = Depends(require_owner)) -> JSONResponse:
    u = user_db.get_user(user_id)
    if not u:
        return JSONResponse(status_code=404, content={"ok": False, "error": "ukendt bruger"})
    return JSONResponse(content={"ok": True, "user": u})


@router.patch("/{user_id}")
def patch_one(user_id: str, req: PatchUserReq,
              claims: dict = Depends(require_owner)) -> JSONResponse:
    if not user_db.get_user(user_id):
        return JSONResponse(status_code=404, content={"ok": False, "error": "ukendt bruger"})
    if req.muted is not None:
        user_db.mute_user(user_id) if req.muted else user_db.unmute_user(user_id)
    if req.tier is not None:
        try:
            user_db.set_quota_tier(user_id, req.tier)
        except ValueError as exc:
            return JSONResponse(status_code=400, content={"ok": False, "error": str(exc)})
    if any(v is not None for v in (req.consent_data_processing, req.consent_marketing,
                                   req.consent_blind_access)):
        user_db.set_consent(user_id, data_processing=req.consent_data_processing,
                            marketing=req.consent_marketing, blind_access=req.consent_blind_access)
    extra: dict[str, Any] = {}
    if req.name is not None:
        extra["name"] = req.name
    if req.role is not None:
        extra["role"] = req.role
    if extra:
        from core.runtime.db import update_user_row
        update_user_row(user_id, extra)
    return JSONResponse(content={"ok": True, "user": user_db.get_user(user_id)})


@router.delete("/{user_id}")
def delete_one(user_id: str, req: DeleteUserReq,
               claims: dict = Depends(require_owner)) -> JSONResponse:
    mode = req.mode if req.mode in ("soft", "hard") else "soft"
    actor = str(claims.get("sub") or "owner")
    ok = user_db.delete_user(user_id, mode=mode, actor=actor)
    if not ok:
        return JSONResponse(status_code=404, content={"ok": False, "error": "ukendt bruger"})
    return JSONResponse(content={"ok": True, "deleted": mode})
