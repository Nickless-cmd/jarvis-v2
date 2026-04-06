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


def maybe_propose_identity_evolution() -> dict[str, object] | None:
    """Analyze personality vector trends and propose IDENTITY.md changes.

    Called weekly via heartbeat idle-action.
    Only proposes if strong patterns are detected.
    """
    try:
        from core.runtime.db import (
            get_latest_cognitive_personality_vector,
            get_latest_cognitive_taste_profile,
            list_cognitive_personality_vectors,
        )
        import json

        current = get_latest_cognitive_personality_vector()
        if not current:
            return None

        version = int(current.get("version", 0))
        if version < 5:
            return None  # Too early — need more data

        # Check if we already have a pending proposal
        pending = [p for p in _PROPOSAL_HISTORY if p.get("status") == "pending"]
        if len(pending) >= 2:
            return None  # Don't spam proposals

        # Analyze personality vector for strong signals
        preferences = json.loads(str(current.get("learned_preferences") or "[]"))
        strengths = json.loads(str(current.get("strengths_discovered") or "[]"))
        bearing = str(current.get("current_bearing") or "")

        # Analyze taste profile
        taste = get_latest_cognitive_taste_profile()
        taste_signals = []
        if taste:
            comm = json.loads(str(taste.get("communication_taste") or "{}"))
            for key, val in comm.items():
                if float(val) > 0.8:
                    taste_signals.append(f"{key.replace('_', ' ')} (stærk præference)")

        if not preferences and not strengths and not taste_signals:
            return None

        # Build proposal
        additions = []
        if strengths:
            additions.append(f"Styrkede domæner: {', '.join(strengths[:3])}")
        if taste_signals:
            additions.append(f"Kommunikations-præferencer: {', '.join(taste_signals[:3])}")
        if bearing:
            additions.append(f"Aktuel retning: {bearing[:80]}")

        proposed = "\n".join(f"- {a}" for a in additions)
        return propose_identity_change(
            target_file="IDENTITY.md",
            proposed_addition=proposed,
            rationale=f"Baseret på personality_vector v{version} og taste_profile trends",
            confidence=min(0.8, 0.4 + version * 0.02),
            evidence_count=version,
        )
    except Exception:
        return None


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
