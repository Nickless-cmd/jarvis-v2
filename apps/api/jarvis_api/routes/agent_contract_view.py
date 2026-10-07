"""Desks laese- og styrings-API til agentkontrakten (agent-contract-v1 G, spec 10).

Ruten er KUN en adapter. Al logik ligger i ``core.services.agent_contract_projection``, saa AgentInspector,
Baggrundsjob-panelet og notifikationsfeedet laeser den samme DB-projektion.

EJEREN er den autentificerede bruger (``current_user_id``) - aldrig et felt i anmodningen. Ingen af
request-modellerne har et ejer- eller sessionsfelt. En andens agent/artefakt er 404, identisk med "findes
ikke". Handlinger genbruger de eksisterende service-funktioner; kvitteringen er ``accepted``, ikke
``delivered``/``stopped``.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents/contract", tags=["agent-contract-view"])

_HTTP = {"POLICY_DENIED": 403, "INVALID_SCOPE": 404, "EXPIRED": 410, "INVALID_TRANSITION": 409,
         "IDEMPOTENCY_CONFLICT": 409, "CAPACITY": 429, "MODEL_UNAVAILABLE": 503, "CLIENT_OFFLINE": 503}


class MessageBody(BaseModel):
    content: str


class FollowupBody(BaseModel):
    goal: str
    idempotency_key: str = ""


class StopBody(BaseModel):
    note: str = ""


def _bruger() -> str:
    from core.identity.workspace_context import current_user_id
    uid = (current_user_id() or "").strip()
    if not uid:
        raise HTTPException(status_code=401, detail="Ikke logget ind")
    return uid


def _ok(out: dict[str, Any]) -> dict[str, Any]:
    if out.get("status") == "error":
        raise HTTPException(status_code=_HTTP.get(str(out.get("code")), 400), detail=out.get("error") or "fejl")
    return out


@router.get("/overview")
async def overview(scope: str = "panel", session: str = "") -> dict:
    """Liste + taellere (aktive og opmaerksomhed er adskilte tal). ``scope=all`` giver hele agenttraeet."""
    from core.services import agent_contract_projection as proj
    uid = _bruger()
    return _ok(await asyncio.to_thread(proj.overview, uid, scope="all" if scope == "all" else "panel",
                                       session_id=session))


@router.get("/agents/{agent_id}")
async def agent(agent_id: str) -> dict:
    from core.services import agent_contract_projection as proj
    uid = _bruger()
    out = await asyncio.to_thread(proj.agent_detail, uid, agent_id)
    if out is None:
        raise HTTPException(status_code=404, detail="Agenten findes ikke")
    return out


@router.get("/agents/{agent_id}/artifacts/{run_id}/{name}")
async def artifact(agent_id: str, run_id: str, name: str, offset: int = 0, limit: int = 20000,
                   session: str = "") -> dict:
    from core.services import agent_contract_projection as proj
    uid = _bruger()
    out = await asyncio.to_thread(proj.read_artifact, uid, agent_id, run_id, name, offset=offset,
                                  limit=max(1, min(int(limit), 200000)), session_id=session)
    if out.get("status") == "NOT_FOUND":
        raise HTTPException(status_code=404, detail="Artefakten findes ikke")
    return out


@router.post("/agents/{agent_id}/message")
async def message(agent_id: str, body: MessageBody) -> dict:
    from core.services import agent_contract_projection as proj
    return _ok(await asyncio.to_thread(proj.send_message, _bruger(), agent_id, body.content))


@router.post("/agents/{agent_id}/followup")
async def followup(agent_id: str, body: FollowupBody) -> dict:
    from core.services import agent_contract_projection as proj
    return _ok(await asyncio.to_thread(proj.followup, _bruger(), agent_id, body.goal,
                                       idempotency_key=body.idempotency_key))


@router.post("/agents/{agent_id}/stop")
async def stop(agent_id: str, body: StopBody | None = None) -> dict:
    from core.services import agent_contract_projection as proj
    return _ok(await asyncio.to_thread(proj.stop, _bruger(), agent_id, (body.note if body else "")))


@router.post("/agents/{agent_id}/close")
async def close(agent_id: str) -> dict:
    from core.services import agent_contract_projection as proj
    return _ok(await asyncio.to_thread(proj.close, _bruger(), agent_id))


@router.get("/feed")
async def feed() -> dict:
    """Kort til notifikationsfeedet (een reference pr. assignment + een pr. ventende approval)."""
    from core.services import agent_contract_projection as proj
    return _ok(await asyncio.to_thread(proj.feed, _bruger()))


@router.post("/feed/{ref_kind}/{ref_id}/read")
async def read(ref_kind: str, ref_id: str) -> dict:
    from core.services import agent_contract_projection as proj
    ok = await asyncio.to_thread(proj.mark_read, _bruger(), ref_kind, ref_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Referencen findes ikke")
    return {"status": "ok", "read": True}


@router.post("/assignments/{assignment_id}/acknowledge")
async def acknowledge(assignment_id: str) -> dict:
    from core.services import agent_contract_projection as proj
    return _ok(await asyncio.to_thread(proj.acknowledge, _bruger(), assignment_id))
