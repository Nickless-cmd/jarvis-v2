"""Contract Evolution — Jarvis proposes changes to his own identity.

Leverages existing V2 systems: self_authored_prompt_proposal,
user_md_update_proposal, memory_md_update_proposal.

Adds: tracking of proposal history, approval workflow, diff generation.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import uuid4

from core.eventbus.bus import event_bus

logger = logging.getLogger(__name__)

_PROPOSAL_HISTORY: list[dict[str, object]] = []


def propose_identity_change(
    *,
    target_file: str,
    proposed_addition: str,
    rationale: str,
    confidence: float = 0.5,
    evidence_count: int = 0,
) -> dict[str, object]:
    """Propose a change to SOUL.md, IDENTITY.md, or USER.md."""
    proposal = {
        "proposal_id": f"evo-{uuid4().hex[:8]}",
        "target_file": target_file,
        "proposed_addition": proposed_addition[:500],
        "rationale": rationale[:200],
        "confidence": round(min(1.0, max(0.0, confidence)), 2),
        "evidence_count": evidence_count,
        "status": "pending",
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }

    _PROPOSAL_HISTORY.append(proposal)
    if len(_PROPOSAL_HISTORY) > 50:
        _PROPOSAL_HISTORY.pop(0)

    event_bus.publish(
        "cognitive_state.contract_proposal",
        {
            "proposal_id": proposal["proposal_id"],
            "target_file": target_file,
            "confidence": confidence,
        },
    )
    return proposal


def approve_proposal(proposal_id: str) -> bool:
    """Mark a proposal as approved (MC action)."""
    for p in _PROPOSAL_HISTORY:
        if p.get("proposal_id") == proposal_id:
            p["status"] = "approved"
            event_bus.publish(
                "cognitive_state.contract_approved",
                {"proposal_id": proposal_id},
            )
            return True
    return False


def reject_proposal(proposal_id: str) -> bool:
    """Mark a proposal as rejected (MC action)."""
    for p in _PROPOSAL_HISTORY:
        if p.get("proposal_id") == proposal_id:
            p["status"] = "rejected"
            event_bus.publish(
                "cognitive_state.contract_rejected",
                {"proposal_id": proposal_id},
            )
            return True
    return False


def build_contract_evolution_surface() -> dict[str, object]:
    pending = [p for p in _PROPOSAL_HISTORY if p.get("status") == "pending"]
    approved = [p for p in _PROPOSAL_HISTORY if p.get("status") == "approved"]
    rejected = [p for p in _PROPOSAL_HISTORY if p.get("status") == "rejected"]
    return {
        "active": bool(_PROPOSAL_HISTORY),
        "pending": pending,
        "approved_count": len(approved),
        "rejected_count": len(rejected),
        "total_proposals": len(_PROPOSAL_HISTORY),
        "summary": (
            f"{len(pending)} pending, {len(approved)} approved, {len(rejected)} rejected"
            if _PROPOSAL_HISTORY else "No contract proposals yet"
        ),
    }
