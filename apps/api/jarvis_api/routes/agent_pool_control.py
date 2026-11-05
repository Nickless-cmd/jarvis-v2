"""Agent-puljen — STYRING fra Desk/PWA: start, interrupt, luk, follow-up. Owner-only.

Ingen ny dispatch-logik og ingen ny agent-model: hver rute kalder PRÆCIS den service
agent-værktøjerne selv bruger (`core.services.agent_contract_service`). Modelruten
valideres af `agent_model_policy.decide_route` inde i `dispatch_agent` (med
`model_required=True`), aldrig af UI'et. En ugyldig rute giver 422 med en brugbar årsag.
"""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/mc/agent-pool", tags=["mc-agent-pool-control"])

DESK_SESSION = "desk-agent-pool"

def _rute_udbydere() -> tuple[str, ...]:
    """De udbydere politikken faktisk kender: CLI-standarderne plus ejer-only-udbyderne.

    Listen er UDLEDT, ikke håndskrevet. En fast liste kom til at love ``ollama``, som
    ikke findes som udbyder noget sted i politikken — UI'et tilbød en rute der altid
    blev afvist ved start."""
    from core.services.agent_cli_backend import DEFAULT_MODELS
    from core.services.agent_model_policy import OWNER_ONLY_PROVIDERS
    ud = list(DEFAULT_MODELS.keys())
    ud += [p for p in sorted(OWNER_ONLY_PROVIDERS) if p not in ud]
    return tuple(ud)

_KODE_TIL_HTTP = {
    "INVALID_SCOPE": 422, "MODEL_UNAVAILABLE": 422, "FORK_COST_UNACCEPTED": 422,
    "POLICY_DENIED": 403, "IDEMPOTENCY_CONFLICT": 409, "CAPACITY": 429,
    "WORKER_UNAVAILABLE": 503, "INVALID_TRANSITION": 409,
}


def _require_owner() -> None:
    from apps.api.jarvis_api.routes.central_auth import require_central_owner
    require_central_owner()


def _owner_id() -> str:
    """Den autentificerede ejer. Uden token (lokal enkeltbruger) er det platformens ejer."""
    try:
        from core.identity.workspace_context import current_user_id
        uid = str(current_user_id() or "").strip()
    except Exception:  # ingen request-kontekst (fx lokal enkeltbruger): fald tilbage til ejeren
        uid = ""
    if uid:
        return uid
    try:
        from core.identity.owner_resolver import owner_user_id
        return str(owner_user_id() or "").strip()
    except Exception:  # ejer kan ikke afgoeres: tom streng -> ruten afviser med 403
        return ""


def _svc():
    from core.services import agent_contract_service
    return agent_contract_service


def _svar(out: dict[str, Any]) -> dict[str, Any]:
    """Servicens fejl bliver til en HTTP-fejl med dens egen årsag — ikke en tavs 200."""
    if isinstance(out, dict) and out.get("status") == "error":
        kode = str(out.get("code") or "")
        raise HTTPException(status_code=_KODE_TIL_HTTP.get(kode, 400), detail={
            "kode": kode, "fejl": out.get("error") or kode, "aarsager": out.get("reasons") or []})
    return out


class StartAgent(BaseModel):
    rolle: str = Field(default="researcher", max_length=60)
    opgave: str = Field(max_length=8000)
    model_route: str = Field(default="", max_length=120)
    workspace: str = Field(default="", max_length=500)
    idempotency_key: str = Field(default="", max_length=120)


class FollowUp(BaseModel):
    opgave: str = Field(max_length=8000)
    idempotency_key: str = Field(default="", max_length=120)


class Afbryd(BaseModel):
    note: str = Field(default="", max_length=500)


def validér_route_syntaks(route: str) -> str:
    """Kun formen (provider/model). Om ruten er TILLADT afgør agent_model_policy."""
    r = (route or "").strip()
    if not r:
        return ""
    udbyder = r.split("/", 1)[0]
    kendte = _rute_udbydere()
    if udbyder not in kendte and "/" in r:
        raise HTTPException(status_code=422, detail={
            "kode": "MODEL_UNAVAILABLE",
            "fejl": f"ukendt udbyder {udbyder!r}; vælg blandt {', '.join(kendte)}",
            "aarsager": []})
    return r


@router.get("/routes")
async def routes() -> dict:
    """Ruter UI'et kan tilbyde — hver enkelt EFTERPRØVET mod politikken.

    En rute der ikke kan vælges lige nu kommer med ``tilgaengelig: false`` og årsagen.
    Så kan listen ikke love noget der alligevel bliver afvist ved start."""
    _require_owner()

    def _byg() -> dict:
        from core.services.agent_cli_backend import DEFAULT_MODELS
        from core.services.agent_model_policy import (
            OWNER_ONLY_PROVIDERS, ModelUnavailable, decide_route)
        owner = _owner_id()
        ruter = []
        for p in _rute_udbydere():
            model = DEFAULT_MODELS.get(p, "")
            eksempel = f"{p}/{model}" if model else f"{p}/"
            tilgaengelig, aarsag = True, ""
            try:
                decide_route(owner_user_id=owner, requested_model=eksempel,
                             hard=True, role="executor")
            except ModelUnavailable as e:
                tilgaengelig, aarsag = False, str(e)[:200]
            except Exception as e:  # en politikfejl må ikke se ud som en rute der virker
                tilgaengelig, aarsag = False, f"{type(e).__name__}: {e}"[:200]
            ruter.append({
                "udbyder": p, "standard_model": model,
                "kun_ejer": p in OWNER_ONLY_PROVIDERS,
                "eksempel": eksempel,
                "tilgaengelig": tilgaengelig, "aarsag": aarsag,
            })
        return {"ruter": ruter}
    return await asyncio.to_thread(_byg)


@router.post("/agents")
async def start(body: StartAgent) -> dict:
    _require_owner()
    route = validér_route_syntaks(body.model_route)
    owner = _owner_id()
    writes = bool((body.workspace or "").strip())
    out = await asyncio.to_thread(
        _svc().dispatch_agent,
        owner_user_id=owner, origin_session_id=DESK_SESSION, goal=body.opgave,
        role=(body.rolle or "researcher").strip() or "researcher",
        expected_result=body.opgave, model=route, model_required=bool(route),
        writes=writes, workspace=body.workspace.strip(),
        idempotency_key=body.idempotency_key, wake_parent=False)
    return _svar(out)


@router.post("/agents/{agent_id}/interrupt")
async def afbryd(agent_id: str, body: Afbryd | None = None) -> dict:
    _require_owner()
    return _svar(await asyncio.to_thread(
        _svc().interrupt_agent, owner_user_id=_owner_id(), origin_session_id=DESK_SESSION,
        agent_id=agent_id, note=(body.note if body else "") or "desk-interrupt"))


@router.post("/agents/{agent_id}/close")
async def luk(agent_id: str) -> dict:
    _require_owner()
    return _svar(await asyncio.to_thread(
        _svc().close_agent, owner_user_id=_owner_id(), origin_session_id=DESK_SESSION,
        agent_id=agent_id))


@router.post("/agents/{agent_id}/followup")
async def opfoelgning(agent_id: str, body: FollowUp) -> dict:
    _require_owner()
    return _svar(await asyncio.to_thread(
        _svc().followup_agent, owner_user_id=_owner_id(), origin_session_id=DESK_SESSION,
        agent_id=agent_id, goal=body.opgave, expected_result=body.opgave,
        idempotency_key=body.idempotency_key, wake_parent=False))
