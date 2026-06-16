"""Connectors-API til jarvis-desk Marketplace (16. jun 2026).

Alt er per-bruger: status, enable/disable og delete bindes til den indloggede
bruger (current_user_id). Ingen bruger kan røre en andens connectors.
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from core.services.connectors import delete_for_user, list_for_user, set_enabled

router = APIRouter()


def _uid() -> str:
    from core.identity.workspace_context import current_user_id
    return current_user_id() or ""


class _EnabledBody(BaseModel):
    enabled: bool


@router.get("/api/connectors")
async def get_connectors() -> JSONResponse:
    uid = _uid()
    if not uid:
        return JSONResponse({"error": "not_authenticated"}, status_code=401)
    return JSONResponse({"connectors": list_for_user(uid)})


@router.post("/api/connectors/{connector_id}/enabled")
async def post_enabled(connector_id: str, body: _EnabledBody) -> JSONResponse:
    uid = _uid()
    if not uid:
        return JSONResponse({"error": "not_authenticated"}, status_code=401)
    ok = set_enabled(uid, connector_id, body.enabled)
    if not ok:
        return JSONResponse({"error": "unknown_connector"}, status_code=404)
    return JSONResponse({"ok": True, "enabled": body.enabled})


@router.delete("/api/connectors/{connector_id}")
async def delete_connector(connector_id: str) -> JSONResponse:
    uid = _uid()
    if not uid:
        return JSONResponse({"error": "not_authenticated"}, status_code=401)
    ok = delete_for_user(uid, connector_id)
    if not ok:
        return JSONResponse({"error": "unknown_connector"}, status_code=404)
    return JSONResponse({"ok": True})
