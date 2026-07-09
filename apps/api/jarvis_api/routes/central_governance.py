from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/central", tags=["central-governance"])


def _require_owner() -> None:
    from apps.api.jarvis_api.routes.central_auth import require_central_owner
    require_central_owner()


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
    # Privilege-eskalering: at flippe et governance-flag kan slå enforcement fra → fail-closed gate.
    from apps.api.jarvis_api.routes.central_auth import require_central_owner_strict
    require_central_owner_strict()
    from core.services.central_governance import set_flag
    return set_flag(body.key, body.value, body.confirm)
