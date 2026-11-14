"""Kontrakt for handlende chat-flader og deres indholdsrevision.

Modulet udfører ikke værktøjer. Det normaliserer tool-gatens udfald og
bevarer den fulde adresse tilbage til den flade, der startede handlingen.
Dermed er ``retryable`` her en egenskab ved handlingen, ikke ved SSE-streamen.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from typing import Any, Callable, Collection

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DeferredTurnAddress:
    account_id: str
    conversation_id: str
    source_message_id: str
    widget_instance_id: str
    content_revision: int = 0

    def public(self) -> dict[str, Any]:
        return {
            "accountId": self.account_id,
            "conversationId": self.conversation_id,
            "sourceMessageId": self.source_message_id,
            "widgetInstanceId": self.widget_instance_id,
            "contentRevision": self.content_revision,
        }


def _fejl(
    adresse: DeferredTurnAddress,
    code: str,
    message: str,
    *,
    retryable: bool,
) -> dict[str, Any]:
    return {
        "status": "failed",
        "retryable": retryable,
        "code": code,
        "message": message,
        "address": adresse.public(),
    }


def afslut_tool_resultat(
    adresse: DeferredTurnAddress,
    raw: Any,
) -> dict[str, Any]:
    """Gør et ægte tool-resultat til en revision af den samme flade."""
    if not isinstance(raw, dict) or not raw:
        return _fejl(
            adresse,
            "invalid_tool_result",
            "Værktøjet returnerede ikke et gyldigt resultat.",
            retryable=False,
        )
    status = str(raw.get("status") or "").strip().lower()
    if status in {"error", "failed", "failure"} or raw.get("error"):
        return _fejl(
            adresse,
            "tool_failed",
            str(raw.get("error") or raw.get("message") or "Værktøjet fejlede."),
            retryable=True,
        )
    naeste = replace(adresse, content_revision=adresse.content_revision + 1)
    return {
        "status": "delivered",
        "retryable": False,
        "result": raw,
        "address": naeste.public(),
    }


def kør_deferred_tool(
    adresse: DeferredTurnAddress,
    *,
    tool_name: str,
    arguments: dict[str, Any],
    allowed_tools: Collection[str],
    execute: Callable[[str, dict[str, Any]], Any],
    register_approval: Callable[[str, dict[str, Any], dict[str, Any]], str] | None = None,
) -> dict[str, Any]:
    """Kør gennem en allerede afgjort gate og behold fladens returadresse."""
    navn = str(tool_name or "").strip()
    if not navn or navn not in allowed_tools:
        return _fejl(
            adresse,
            "component_unavailable",
            "Værktøjet er ikke tilgængeligt i denne chat.",
            retryable=False,
        )
    try:
        raw = execute(navn, dict(arguments or {}))
    except Exception as fejl:  # værktøjet må fejle uden at vælte turen — men fejlen skal ses
        logger.warning("flade-deferred-turn: værktøjet %s kastede: %s", navn, fejl)
        return _fejl(adresse, "tool_failed", str(fejl), retryable=True)
    if isinstance(raw, dict) and str(raw.get("status") or "") == "approval_needed":
        if register_approval is None:
            return _fejl(
                adresse,
                "component_unavailable",
                "Godkendelsesvejen er ikke tilgængelig.",
                retryable=False,
            )
        approval_id = register_approval(navn, dict(arguments or {}), raw)
        return {
            "status": "approval_required",
            "retryable": False,
            "approvalId": approval_id,
            "address": adresse.public(),
        }
    return afslut_tool_resultat(adresse, raw)


def aflæs_approval_resultat(
    adresse: DeferredTurnAddress,
    state: Any,
    *,
    approval_id: str = "",
) -> dict[str, Any]:
    """Projicér approval-runtimens delte state tilbage i den oprindelige flade."""
    if not isinstance(state, dict) or not state:
        return _fejl(
            adresse, "component_unavailable",
            "Godkendelsen findes ikke længere.", retryable=False,
        )
    status = str(state.get("status") or "pending").strip().lower()
    if status in {"pending", "resolving"}:
        return {
            "status": "approval_required",
            "retryable": False,
            "approvalId": approval_id or str(state.get("approval_id") or ""),
            "address": adresse.public(),
        }
    if status == "denied":
        return _fejl(
            adresse, "tool_failed", "Godkendelsen blev afvist.", retryable=False,
        )
    if status != "approved":
        return _fejl(
            adresse, "tool_failed",
            str(state.get("error") or "Godkendelsen kunne ikke gennemføres."),
            retryable=True,
        )
    tool_status = str(state.get("tool_status") or "ok").strip().lower()
    raw = {
        "status": tool_status,
        "result": state.get("result_text"),
    }
    return afslut_tool_resultat(adresse, raw)
