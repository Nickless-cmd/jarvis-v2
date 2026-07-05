from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/central", tags=["central-healers"])

_VALID_FLAGS = {"enabled", "daemon_restart_live", "syslog_restart_live"}


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


class HealerFlagBody(BaseModel):
    name: str
    enabled: bool
    confirm: bool = False


@router.get("/healers")
async def get_healers() -> dict:
    _require_owner()
    from core.services.error_healers import build_healer_surface
    return build_healer_surface()


@router.post("/healers/flag")
async def set_healer(body: HealerFlagBody) -> dict:
    _require_owner()
    if body.name not in _VALID_FLAGS:
        return {"ok": False, "error": f"ukendt healer-flag: {body.name}"}
    if not body.confirm:
        return {"ok": False, "needs_confirm": True}  # alle healer-flags er farlige
    from core.services.error_healers import set_healer_flag
    res = set_healer_flag(body.name, body.enabled)
    try:
        from core.services.central_governance import record_mutation
        record_mutation("healing", body.name, body.enabled)
    except Exception:
        pass
    return {"ok": True, "name": body.name, "enabled": body.enabled, "result": res}
