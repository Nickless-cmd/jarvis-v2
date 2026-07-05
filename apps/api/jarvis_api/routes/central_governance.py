from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/central", tags=["central-governance"])


def _require_owner() -> None:
    from core.identity.workspace_context import current_user_id
    uid = current_user_id() or None
    if uid is None:
        return
    try:
        from core.identity.users import find_user_by_discord_id
        if getattr(find_user_by_discord_id(str(uid)), "role", "") == "owner":
            return
    except Exception:
        pass
    raise HTTPException(status_code=403, detail="Centralen er kun for owner")


class SetFlagBody(BaseModel):
    key: str
    value: object
    confirm: bool = False


@router.get("/governance")
async def get_governance() -> dict:
    _require_owner()
    from core.services.central_governance import list_flags
    return {"flags": list_flags()}


@router.post("/governance/set")
async def set_governance(body: SetFlagBody) -> dict:
    _require_owner()
    from core.services.central_governance import set_flag
    return set_flag(body.key, body.value, body.confirm)
