"""Agent-approvals: list og afgoer (agent-contract-v1 F4c, spec 8.2).

Kun en AUTENTIFICERET bruger kan afgoere, og kun ejerens/platformens ejers egne approvals (det haandhaeves
i ``db_agent_approvals.decide`` - ruten er kun adapteren). Jarvis, en agent og en model har ingen vej hertil
med et menneskes identitet: ruten saetter ``actor_kind="human"`` KUN naar anmodningen bærer en indlogget brugers
token.

SIKKERHEDEN ER IDENTITETEN, IKKE EN KODE (14/10-2026). Her stod der indtil i dag at en godkendelse kraevede
brugerens totrinskode. Det var en fejl, og Bjoerns egen spec siger det modsatte
(``2026-06-14-totp-override-security-design.md`` §6.1): TOTP kraeves i en FREMMED session - «Owner i sin EGEN
desk-session: INGEN TOTP, sessionen er allerede kryptografisk bundet til owner». Hele override-flowet (§6.3)
forudsaetter endda eksplicit «Bjoern er i en fremmed sessions-kontekst».

To ting baerer sikkerheden her, og begge er staerkere end en 6-cifret kode mod det trusselbillede der er
relevant: (1) et autentificeret token, som ruten kraever (401 uden) og ``decide`` binder til ejeren; (2)
``session``-bindingen - anmodningen maa oplyse sin session, og ``decide`` afviser den hvis den ikke er den
approvalen blev foedt i. En TOTP beskyttede kun mod en STJAALET token, og en angriber med token'en kan ogsaa
laese sessions-listen og faa id'et; til gengaeld ramte den den legitime ejer hver eneste gang.
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
    #: Sessionen anmodningen kommer fra. Klienten kender sin egen session og sender den med; ``decide``
    #: afviser en session der ikke er den approvalen blev foedt i. Tom = klienten oplyser ikke sin session,
    #: og identiteten baeres da alene af token'en (se modulets docstring).
    session: str = ""


def _bruger() -> str:
    from core.identity.workspace_context import current_user_id
    uid = (current_user_id() or "").strip()
    if not uid:
        raise HTTPException(status_code=401, detail="Ikke logget ind")
    return uid


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
    from core.services import agent_contract_service as svc
    out = await asyncio.to_thread(
        svc.decide_approval, approval_id=approval_id, decision=body.decision, actor_user_id=uid,
        actor_kind="human", digest=body.digest, note=body.note, actor_session_id=body.session)
    if out.get("status") == "error":
        raise HTTPException(status_code=_HTTP.get(out["code"], 400), detail=out["error"])
    return out
