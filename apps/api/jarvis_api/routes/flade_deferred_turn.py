"""Chat-fladers direkte, adresserede tool-turns.

Ruten genbruger ``simple_tools.execute_tool`` og chat-scope. Den kalder aldrig
force-varianten; approval-resultater sendes videre til den eksisterende
approval-runtime.
"""
from __future__ import annotations

from typing import Any

import asyncio
from types import SimpleNamespace

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.tools.simple_tools import execute_tool, get_tool_definitions
from core.tools.tool_scoping import reset_tool_scope, set_tool_scope
from core.services.flade_deferred_turn import (
    DeferredTurnAddress,
    aflæs_approval_resultat,
    kør_deferred_tool,
)

router = APIRouter(prefix="/chat", tags=["chat"])


class DeferredTurnAddressBody(BaseModel):
    accountId: str = ""
    conversationId: str
    sourceMessageId: str
    widgetInstanceId: str
    contentRevision: int = Field(default=0, ge=0)


class DeferredToolTurnBody(BaseModel):
    address: DeferredTurnAddressBody
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class DeferredApprovalStatusBody(BaseModel):
    address: DeferredTurnAddressBody
    approvalId: str


def _current_user_id() -> str:
    from core.identity.workspace_context import current_user_id
    return str(current_user_id() or "").strip()


def _kraev_adgang(session_id: str) -> None:
    from apps.api.jarvis_api.routes.chat_session_view import kraev_adgang
    kraev_adgang(session_id)


def _source_message_belongs(message_id: str, session_id: str) -> bool:
    from core.runtime.db import connect
    with connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM chat_messages WHERE message_id = ? AND session_id = ? "
            "AND role = 'assistant' LIMIT 1",
            (message_id, session_id),
        ).fetchone()
    return row is not None


def _adresse(body: DeferredTurnAddressBody) -> DeferredTurnAddress:
    return DeferredTurnAddress(
        account_id=body.accountId.strip(),
        conversation_id=body.conversationId.strip(),
        source_message_id=body.sourceMessageId.strip(),
        widget_instance_id=body.widgetInstanceId.strip(),
        content_revision=body.contentRevision,
    )


def _validér_adresse(body: DeferredTurnAddressBody) -> DeferredTurnAddress:
    adresse = _adresse(body)
    if not all((adresse.conversation_id, adresse.source_message_id, adresse.widget_instance_id)):
        raise HTTPException(status_code=400, detail="Deferred-turn-adressen er ufuldstændig")
    _kraev_adgang(adresse.conversation_id)
    bruger = _current_user_id()
    if adresse.account_id and bruger and adresse.account_id != bruger:
        raise HTTPException(status_code=403, detail="Deferred-turn-adressen tilhører en anden konto")
    if not adresse.account_id:
        adresse = DeferredTurnAddress(
            account_id=bruger,
            conversation_id=adresse.conversation_id,
            source_message_id=adresse.source_message_id,
            widget_instance_id=adresse.widget_instance_id,
            content_revision=adresse.content_revision,
        )
    if not _source_message_belongs(adresse.source_message_id, adresse.conversation_id):
        raise HTTPException(status_code=404, detail="Kildebeskeden findes ikke i samtalen")
    return adresse


def _register_approval(
    adresse: DeferredTurnAddress,
    tool_name: str,
    arguments: dict[str, Any],
    raw: dict[str, Any],
) -> str:
    """Byg kortet gennem samme approval-runtime som synlige model-runs."""
    import core.services.approval_runtime as approval_runtime
    import core.services.visible_runs as visible_runs

    approval_id = approval_runtime.new_id()
    run = SimpleNamespace(
        run_id=f"deferred-{adresse.widget_instance_id}",
        session_id=adresse.conversation_id,
        surface="chat",
        user_id=_current_user_id(),
    )
    kort = approval_runtime.build_request(
        tool_name=tool_name, arguments=arguments, result=raw, run=run,
    )
    visible_runs.saet_godkendelse(approval_id, kort)
    visible_runs._set_visible_approval_state(approval_id, {
        **kort, "approval_id": approval_id, "status": "pending",
    })
    visible_runs._publicer_approval_requested(
        approval_id=approval_id,
        tool=tool_name,
        run_id=run.run_id,
        session_id=run.session_id,
        result=raw,
    )
    return approval_id


def _execute_chat_tool(
    tool_name: str, arguments: dict[str, Any],
) -> tuple[dict[str, Any] | None, set[str]]:
    """Bind chat-scope omkring BÅDE katalogopslag og udførelse."""
    token = set_tool_scope("chat")
    try:
        definitioner = get_tool_definitions(scope="chat")
        tilladte = {
            str((d.get("function") or {}).get("name") or "")
            for d in definitioner if isinstance(d, dict)
        }
        tilladte.discard("")
        if tool_name not in tilladte:
            return None, tilladte
        return execute_tool(tool_name, arguments), tilladte
    finally:
        reset_tool_scope(token)


@router.post("/flade/deferred-turn")
async def flade_deferred_tool_turn(body: DeferredToolTurnBody) -> dict[str, Any]:
    adresse = _validér_adresse(body.address)
    raw, allowed = await asyncio.to_thread(
        _execute_chat_tool, body.tool.strip(), dict(body.arguments or {}),
    )
    return kør_deferred_tool(
        adresse,
        tool_name=body.tool,
        arguments=body.arguments,
        allowed_tools=allowed,
        # Resultatet er allerede udført gennem gaten ovenfor. Denne callable
        # må ikke kalde igen; den afleverer kun udfaldet til normaliseringen.
        execute=lambda _navn, _args: raw,
        register_approval=lambda navn, args, resultat: _register_approval(
            adresse, navn, args, resultat,
        ),
    )


@router.post("/flade/deferred-turn/status")
async def flade_deferred_tool_status(body: DeferredApprovalStatusBody) -> dict[str, Any]:
    adresse = _validér_adresse(body.address)
    import core.services.visible_runs as visible_runs
    state = visible_runs._get_visible_approval_state(body.approvalId.strip())
    if state and str(state.get("session_id") or "") != adresse.conversation_id:
        raise HTTPException(status_code=404, detail="Godkendelsen hører ikke til samtalen")
    return aflæs_approval_resultat(
        adresse, state, approval_id=body.approvalId.strip(),
    )
