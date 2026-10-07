"""Workspace-tillid som sin egen rute-flade — udskilt fra `chat.py` 3/10-2026.

Boy Scout: `chat.py` stod paa 2.006 linjer, og tilladelses-arven nedenfor
roerer dens session-oprettelse. De tre tillids-ruter er den naermeste naturlige
enhed: samme spoergsmaal — hvem maa hvad, hvor — og de har ingen afhaengighed
til resten af `chat.py` ud over `current_user_id`.

Ruterne er UAENDREDE i adfaerd og URL (`/chat/workspace-trust`), saa ingen
klient maerker flytningen. `core.services.workspace_trust` baerer selve reglen,
inklusive arven ned i undermapper — se dens `is_trusted`.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/chat", tags=["chat"])


class WorkspaceTrustRequest(BaseModel):
    kind: str = "container"
    root: str = ""
    trusted: bool = True


@router.get("/workspace-trust")
def get_workspace_trust(kind: str = "container", root: str = "") -> dict:
    """Er det aktuelle workspace betroet for den indloggede bruger?"""
    from core.identity.workspace_context import current_user_id
    from core.services.workspace_trust import is_trusted
    uid = current_user_id() or None
    return {"kind": kind, "root": root, "trusted": is_trusted(uid, kind, root)}


@router.get("/workspace-trust/list")
def list_workspace_trust(kind: str = "") -> dict:
    """De mapper brugeren har betroet — grundlaget for workstation-vaelgeren.

    Uden den her kunne desk kun spoerge «er DENNE mappe betroet?», og en
    vaelger skal kende kandidaterne foer den kan vise dem.
    """
    from core.identity.workspace_context import current_user_id
    from core.services.workspace_trust import list_trusted
    uid = current_user_id() or None
    return {"folders": list_trusted(uid, kind or None)}


@router.post("/workspace-trust")
def set_workspace_trust(request: WorkspaceTrustRequest) -> dict:
    """Markér/afmarkér et workspace som betroet (skrive/exec-gate i code-mode)."""
    from core.identity.workspace_context import current_user_id
    from core.services.workspace_trust import set_trusted
    if not request.root.strip():
        raise HTTPException(status_code=400, detail="root må ikke være tom")
    uid = current_user_id() or None
    trusted = set_trusted(uid, request.kind, request.root, request.trusted)
    return {"kind": request.kind, "root": request.root, "trusted": trusted}
