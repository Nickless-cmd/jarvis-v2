"""Autonomy proposal queue — Niveau 2 fundament.

Holder strukturerede proposals fra Jarvis der venter på Bjørns
godkendelse. Dette er en separat lane fra capability-approvals
fordi:

- Capability approvals er per-call og kortvarige
- Autonomy proposals er forslag om bounded actions Jarvis vil tage
  selv hvis han fik lov, og kan godkendes asynkront via MC

Proposals har en kind, en payload, og et eksekvering-løfte.
Når en proposal approves kalder service'en den korrekte executor
og opdaterer status til executed eller failed.

Design-principper:
- Aldrig auto-approval (Bjørn er gate)
- Aldrig irreversible actions uden eksplicit confirmation
- Hver kind har sin egen executor — ny kind = ny handler
- Alle execution attempts logges som event for audit
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Callable
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import (
    create_autonomy_proposal,
    get_autonomy_proposal,
    list_autonomy_proposals,
    resolve_autonomy_proposal,
)

logger = logging.getLogger(__name__)


# Registry of executors per kind. Each executor takes the proposal
# payload and returns an execution result dict. Register additional
# kinds via register_proposal_executor().
_PROPOSAL_EXECUTORS: dict[str, Callable[[dict], dict]] = {}


def register_proposal_executor(kind: str, fn: Callable[[dict], dict]) -> None:
    """Register an executor for a proposal kind."""
    _PROPOSAL_EXECUTORS[kind] = fn


def get_registered_proposal_kinds() -> list[str]:
    return sorted(_PROPOSAL_EXECUTORS.keys())


def file_proposal(
    *,
    kind: str,
    title: str,
    rationale: str = "",
    payload: dict | None = None,
    created_by: str = "",
    session_id: str = "",
    run_id: str = "",
    tick_id: str = "",
    canonical_key: str = "",
) -> dict[str, object]:
    """File a new proposal in the queue.

    Returns the persisted proposal record (with generated proposal_id).
    """
    proposal_id = f"prop-{uuid4().hex[:16]}"
    proposal = create_autonomy_proposal(
        proposal_id=proposal_id,
        kind=kind,
        title=title.strip()[:200],
        rationale=rationale.strip()[:1000],
        payload=payload or {},
        created_by=created_by,
        session_id=session_id,
        run_id=run_id,
        tick_id=tick_id,
        canonical_key=canonical_key,
    )
    try:
        event_bus.publish(
            "autonomy_proposal.filed",
            {
                "proposal_id": proposal_id,
                "kind": kind,
                "title": title[:120],
                "created_by": created_by,
            },
        )
    except Exception:
        pass
    return proposal


def list_pending_proposals(*, limit: int = 50) -> list[dict[str, object]]:
    return list_autonomy_proposals(status="pending", limit=limit)


def list_recent_proposals(*, limit: int = 50) -> list[dict[str, object]]:
    return list_autonomy_proposals(limit=limit)


def approve_proposal(
    proposal_id: str,
    *,
    resolution_note: str = "",
) -> dict[str, object]:
    """Bjørn approves a proposal — execute it immediately if we have an
    executor for the kind, otherwise just mark as approved.
    """
    proposal = get_autonomy_proposal(proposal_id)
    if not proposal:
        return {"status": "not-found", "proposal_id": proposal_id}
    if str(proposal.get("status") or "") != "pending":
        return {
            "status": "not-pending",
            "proposal_id": proposal_id,
            "current_status": proposal.get("status"),
        }
    kind = str(proposal.get("kind") or "")
    executor = _PROPOSAL_EXECUTORS.get(kind)
    if executor is None:
        # Approved but we have no executor — mark approved without executing
        resolved = resolve_autonomy_proposal(
            proposal_id,
            status="approved",
            resolved_by="bjorn",
            resolution_note=resolution_note or "Approved — no executor registered",
        )
        try:
            event_bus.publish(
                "autonomy_proposal.approved_no_executor",
                {"proposal_id": proposal_id, "kind": kind},
            )
        except Exception:
            pass
        return {"status": "approved", "proposal": resolved}
    # Execute
    payload = proposal.get("payload") or {}
    try:
        result = executor(dict(payload) if isinstance(payload, dict) else {})
    except Exception as exc:
        logger.exception("autonomy proposal executor failed for %s", kind)
        resolved = resolve_autonomy_proposal(
            proposal_id,
            status="failed",
            resolved_by="executor",
            resolution_note=f"Executor raised: {exc}",
            execution_result={"error": str(exc)},
        )
        try:
            event_bus.publish(
                "autonomy_proposal.execution_failed",
                {"proposal_id": proposal_id, "kind": kind, "error": str(exc)},
            )
        except Exception:
            pass
        return {"status": "failed", "proposal": resolved, "error": str(exc)}
    resolved = resolve_autonomy_proposal(
        proposal_id,
        status="executed",
        resolved_by="bjorn",
        resolution_note=resolution_note or "Approved and executed",
        execution_result=result if isinstance(result, dict) else {"value": result},
    )
    try:
        event_bus.publish(
            "autonomy_proposal.executed",
            {
                "proposal_id": proposal_id,
                "kind": kind,
                "result_summary": str(result)[:200] if result else "",
            },
        )
    except Exception:
        pass
    return {"status": "executed", "proposal": resolved}


def reject_proposal(
    proposal_id: str,
    *,
    resolution_note: str = "",
) -> dict[str, object]:
    proposal = get_autonomy_proposal(proposal_id)
    if not proposal:
        return {"status": "not-found", "proposal_id": proposal_id}
    if str(proposal.get("status") or "") != "pending":
        return {
            "status": "not-pending",
            "proposal_id": proposal_id,
            "current_status": proposal.get("status"),
        }
    resolved = resolve_autonomy_proposal(
        proposal_id,
        status="rejected",
        resolved_by="bjorn",
        resolution_note=resolution_note or "Rejected",
    )
    try:
        event_bus.publish(
            "autonomy_proposal.rejected",
            {"proposal_id": proposal_id, "kind": str(proposal.get("kind") or "")},
        )
    except Exception:
        pass
    return {"status": "rejected", "proposal": resolved}


def build_autonomy_proposal_surface(*, limit: int = 20) -> dict[str, object]:
    """MC-friendly view of the proposal queue."""
    pending = list_pending_proposals(limit=limit)
    recent = list_recent_proposals(limit=limit)
    return {
        "active": bool(pending),
        "pending_count": len(pending),
        "registered_kinds": get_registered_proposal_kinds(),
        "items": pending,
        "recent": recent,
        "summary": (
            f"{len(pending)} autonomy proposal(s) awaiting Bjørn approval"
            if pending
            else "No autonomy proposals pending"
        ),
    }


# ---------------------------------------------------------------------------
# Built-in executors
# ---------------------------------------------------------------------------


def _execute_memory_rewrite_proposal(payload: dict) -> dict:
    """Execute an approved memory-rewrite proposal.

    Payload schema:
        {"target": "MEMORY.md" | "USER.md", "new_content": "..."}
    """
    from core.tools.workspace_capabilities import invoke_workspace_capability

    target = str(payload.get("target") or "MEMORY.md")
    new_content = str(payload.get("new_content") or "")
    if not new_content:
        return {"status": "error", "error": "missing new_content in payload"}
    result = invoke_workspace_capability(
        "tool:rewrite-workspace-memory",
        write_content=new_content,
        approved=True,
        target_path=target,
    )
    return {
        "status": result.get("status"),
        "detail": result.get("detail"),
        "result": result.get("result"),
    }


# Register built-ins on import
register_proposal_executor("memory-rewrite", _execute_memory_rewrite_proposal)
