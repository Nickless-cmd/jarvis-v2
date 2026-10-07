"""Agent-approvals: list og afgoer (agent-contract-v1 F4c, spec 8.2).

Kun en AUTENTIFICERET bruger kan afgoere, og kun ejerens/platformens ejers egne approvals (det haandhaeves
i ``db_agent_approvals.decide`` - ruten er kun adapteren). Jarvis, en agent og en model har ingen vej hertil
med et menneskes identitet: ruten saetter ``actor_kind="human"`` KUN naar anmodningen bærer en indlogget brugers
token, og en GODKENDELSE kraever desuden brugerens totrinskode, hvis han har sat en op - Jarvis kender den ikke,
selv om han kan kalde API'et med ejerens token. Et AFSLAG kraever ingen kode (det er altid sikkert).
"""
from __future__ import annotations

import asyncio
import logging
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents/approvals", tags=["agent-approvals"])

_HTTP = {"POLICY_DENIED": 403, "INVALID_SCOPE": 404, "EXPIRED": 410, "INVALID_TRANSITION": 409}


class DecisionRequest(BaseModel):
    decision: Literal["approve", "deny"]
    digest: str
    note: str = ""
    kode: str = ""          # totrinskoden - kraeves ved godkendelse naar brugeren har en


def _bruger() -> str:
    from core.identity.workspace_context import current_user_id
    uid = (current_user_id() or "").strip()
    if not uid:
        raise HTTPException(status_code=401, detail="Ikke logget ind")
    return uid


def _kraev_totrin_ved_godkendelse(uid: str, kode: str) -> None:
    from core.identity.users import get_totp_seed
    seed = get_totp_seed(discord_id=uid)
    if not seed:
        logger.warning("approval godkendt af %s UDEN totrinskode (ingen sat op)", uid)
        return
    from core.services.device_pairing import TotpFejl, kraev_totp
    try:
        kraev_totp(uid, kode)
    except TotpFejl as exc:
        raise HTTPException(status_code=exc.kode, detail=str(exc)) from exc


@router.get("")
async def list_approvals(status: str = "", session: str = "") -> dict:
    """Brugerens egne approvals med sikker visning og digest (aldrig raa argumenter)."""
    uid = _bruger()
    from core.services import agent_contract_service as svc
    out = await asyncio.to_thread(svc.list_approvals, owner_user_id=uid, status=status, origin_session_id=session)
    if out.get("status") == "error":
        raise HTTPException(status_code=_HTTP.get(out["code"], 400), detail=out["error"])
    return out


@router.post("/{approval_id}/decision")
async def decide(approval_id: str, body: DecisionRequest) -> dict:
    uid = _bruger()
    if body.decision == "approve":
        await asyncio.to_thread(_kraev_totrin_ved_godkendelse, uid, body.kode)
    from core.services import agent_contract_service as svc
    out = await asyncio.to_thread(
        svc.decide_approval, approval_id=approval_id, decision=body.decision, actor_user_id=uid,
        actor_kind="human", digest=body.digest, note=body.note)
    if out.get("status") == "error":
        raise HTTPException(status_code=_HTTP.get(out["code"], 400), detail=out["error"])
    return out
