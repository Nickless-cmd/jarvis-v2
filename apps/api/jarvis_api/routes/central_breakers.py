from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/central", tags=["central-breakers"])


def _require_owner() -> None:
    from apps.api.jarvis_api.routes.central_auth import require_central_owner
    require_central_owner()


def _reset_breaker(nerve: str) -> None:
    """Nulstil breaker for nerven på central-singletonen. Self-safe."""
    from core.services.central_core import central
    central()._breaker.reset(nerve)


class ResetBody(BaseModel):
    confirm: bool = False


@router.post("/breakers/{nerve:path}/reset")
async def reset_breaker(nerve: str, body: ResetBody) -> dict:
    _require_owner()
    if not body.confirm:
        return {"ok": False, "needs_confirm": True}
    try:
        _reset_breaker(nerve)
    except Exception as exc:
        return {"ok": False, "error": f"reset fejlede: {exc!s}"[:200]}
    try:
        from core.services.central_governance import record_mutation
        record_mutation("breaker", nerve, "reset")
    except Exception:
        pass
    return {"ok": True, "nerve": nerve, "action": "reset"}
