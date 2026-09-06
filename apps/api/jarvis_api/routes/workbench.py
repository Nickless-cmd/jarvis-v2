"""Ruter til de værktøjer der blev bygget 6/9 men aldrig kunne nås fra en app.

Operator-kanalen og redigerings-checkpointet fandtes som værktøjer Jarvis
kunne kalde — men uden en rute kunne Bjørn hverken se eller styre dem fra
desk og mobil. For kanalen er det et sikkerhedsproblem og ikke bare
ubelejligt: mens den er åben, kører `bash` på hans maskine uden godkendelse
pr. kald, i op til fire timer, og han havde ingen måde at se det på.

Begge er owner-only. Læsning af status er ikke: at spørge om kanalen er åben
er harmløst, og at gate det ville bare skjule tilstanden for den der har mest
brug for at se den.
"""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Body, HTTPException

from apps.api.jarvis_api.routes.account import _current_role
from core.identity.workspace_context import current_context_snapshot

router = APIRouter(prefix="/workbench", tags=["workbench"])


def _kraev_owner(hvad: str) -> None:
    snap = current_context_snapshot()
    if _current_role(snap.get("user_id") or "") != "owner":
        raise HTTPException(status_code=403, detail=f"{hvad} kan kun styres af owner")


def _session_id(payload: dict | None = None) -> str:
    sid = str((payload or {}).get("session_id") or "").strip()
    if sid:
        return sid
    from core.services.operator_channel import current_session_id
    return current_session_id()


# ── Operator-kanal ──────────────────────────────────────────────────────────

@router.get("/operator-channel")
async def operator_channel_status(session_id: str = "") -> dict[str, Any]:
    """Er kanalen åben, og hvor længe endnu? Læse-kun, ingen owner-gate."""
    from core.services.operator_channel import status
    sid = session_id or _session_id()
    return await asyncio.to_thread(status, sid)


@router.post("/operator-channel/open")
async def operator_channel_open(payload: dict = Body(default={})) -> dict[str, Any]:
    """Owner-only: åbn kanalen. Herefter kører bash på Bjørns maskine."""
    _kraev_owner("Operator-kanalen")
    from core.services.operator_channel import open_channel
    sid = _session_id(payload)
    return await asyncio.to_thread(lambda: open_channel(sid, is_owner=True))


@router.post("/operator-channel/close")
async def operator_channel_close(payload: dict = Body(default={})) -> dict[str, Any]:
    _kraev_owner("Operator-kanalen")
    from core.services.operator_channel import close_channel
    sid = _session_id(payload)
    return await asyncio.to_thread(lambda: close_channel(sid, is_owner=True))


# ── Redigerings-checkpoints ─────────────────────────────────────────────────

@router.get("/checkpoints")
async def checkpoints_list(session_id: str = "") -> dict[str, Any]:
    """Hvad kan fortrydes? Nyeste først."""
    from core.services.edit_checkpoint import list_checkpoints
    sid = session_id or _session_id()
    punkter = await asyncio.to_thread(list_checkpoints, sid)
    return {
        "status": "ok",
        "antal": len(punkter),
        "punkter": [
            {"sha": str(p.get("sha") or "")[:10], "note": p.get("note"),
             "cwd": p.get("cwd"), "tid": p.get("tid")}
            for p in reversed(punkter)
        ][:20],
    }


@router.post("/checkpoints/rollback")
async def checkpoints_rollback(payload: dict = Body(default={})) -> dict[str, Any]:
    """Owner-only: rul den seneste redigeringsrunde tilbage som helhed.

    Rører kun arbejdstræ og index — aldrig HEAD, aldrig grenen.
    """
    _kraev_owner("Checkpoints")
    from core.services.edit_checkpoint import rollback_last
    sid = _session_id(payload)
    return await asyncio.to_thread(rollback_last, sid)


# ── Kontakter (sandbox + env-blok) ──────────────────────────────────────────

@router.get("/switches")
async def switches_status() -> dict[str, Any]:
    """Tilstand for de to kontakter der styrer runtime-adfærd fra UI'et."""
    def _saml() -> dict[str, Any]:
        from core.services.bash_sandbox import status as sandbox_status
        from core.services.env_block import is_enabled as env_on
        return {
            "status": "ok",
            "bash_sandbox": sandbox_status(),
            "env_block": {"tændt": env_on()},
        }
    return await asyncio.to_thread(_saml)


@router.post("/switches/{navn}")
async def switch_set(navn: str, payload: dict = Body(default={})) -> dict[str, Any]:
    """Owner-only: tænd/sluk `bash_sandbox` eller `env_block`. Body: {enabled: bool}."""
    _kraev_owner("Runtime-kontakter")
    on = bool((payload or {}).get("enabled"))

    def _saet() -> dict[str, Any]:
        if navn == "bash_sandbox":
            from core.services.bash_sandbox import set_enabled, status
            set_enabled(on)
            return {"status": "ok", "bash_sandbox": status()}
        if navn == "env_block":
            from core.services import central_switches
            from core.services.env_block import is_enabled
            from core.services.gate_kernel import GateClass
            central_switches.set_enabled("prompt", "env_block", on,
                                         klass=GateClass.COGNITIVE)
            return {"status": "ok", "env_block": {"tændt": is_enabled()}}
        raise HTTPException(status_code=404, detail=f"ukendt kontakt: {navn}")

    return await asyncio.to_thread(_saet)


# ── Kontekst-drawer ─────────────────────────────────────────────────────────

@router.get("/context")
async def context_summary(session_id: str = "") -> dict[str, Any]:
    """Hvad gik der ind i sidste tur? Filer, kilder, størrelse.

    Retrospektivt med vilje. Et estimat FØR afsendelse ville være et gæt
    præsenteret som en måling, og prompten koster sekunder at bygge — en
    drawer man venter på er en drawer man lukker.

    Kun navne og tal, aldrig indhold: spørgsmålet er «hvad bruger han»,
    ikke «gengiv hans hukommelse i et sidepanel».
    """
    def _hent() -> dict[str, Any]:
        from core.services.prompt_contract import kontekst_resume
        sid = session_id or _session_id()
        r = kontekst_resume(sid)
        if not r:
            return {"status": "ok", "har_data": False, "session_id": sid}
        return {
            "status": "ok", "har_data": True, "session_id": sid,
            "filer": r.get("filer") or [],
            "udeladt": r.get("udeladt") or [],
            "kilder": r.get("kilder") or [],
            "tegn": r.get("tegn") or 0,
            "dele": r.get("dele") or 0,
        }
    return await asyncio.to_thread(_hent)
