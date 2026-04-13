"""Thought-action proposal daemon — turns action impulses in thought stream into MC proposals."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record
from apps.api.jarvis_api.services.proposal_classifier import classify_fragment

_MAX_PENDING = 10
_MAX_RESOLVED = 20

_pending_proposals: list[dict] = []
_resolved_proposals: list[dict] = []
_last_classified_fragment: str = ""


def tick_thought_action_proposal_daemon(fragment: str) -> dict[str, object]:
    """Classify fragment and create a proposal if an action impulse is detected."""
    global _last_classified_fragment

    if not fragment or fragment == _last_classified_fragment:
        return {"generated": False}

    _last_classified_fragment = fragment
    classification = classify_fragment(fragment)

    if not classification["has_action"]:
        return {"generated": False}

    if len(_pending_proposals) >= _MAX_PENDING:
        return {"generated": False}

    proposal = {
        "id": f"tap-{uuid4().hex[:12]}",
        "fragment_excerpt": fragment[:120],
        "action_description": classification["action_description"],
        "proposal_type": classification["proposal_type"],
        "destructive_score": classification["destructive_score"],
        "destructive_reason": classification["destructive_reason"],
        "status": "pending",
        "created_at": datetime.now(UTC).isoformat(),
    }
    _pending_proposals.append(proposal)

    try:
        insert_private_brain_record(
            record_id=f"pb-tap-{uuid4().hex[:12]}",
            record_type="thought-action-proposal",
            layer="private_brain",
            session_id="heartbeat",
            run_id=f"tap-daemon-{uuid4().hex[:12]}",
            focus="handlingsimpuls",
            summary=classification["action_description"],
            detail=f"fragment={fragment[:80]} type={classification['proposal_type']}",
            source_signals="thought-action-proposal-daemon:heartbeat",
            confidence="low",
            created_at=proposal["created_at"],
        )
    except Exception:
        pass

    try:
        event_bus.publish(
            "thought_action_proposal.created",
            {
                "proposal_id": proposal["id"],
                "proposal_type": proposal["proposal_type"],
                "action_description": proposal["action_description"],
            },
        )
    except Exception:
        pass

    return {"generated": True, "proposal": proposal}


def resolve_proposal(proposal_id: str, decision: str) -> bool:
    """Move a proposal from pending to resolved. decision: 'approved' | 'dismissed'."""
    global _pending_proposals, _resolved_proposals

    for i, p in enumerate(_pending_proposals):
        if p["id"] == proposal_id:
            resolved = {**p, "status": decision, "resolved_at": datetime.now(UTC).isoformat()}
            _pending_proposals.pop(i)
            _resolved_proposals.insert(0, resolved)
            if len(_resolved_proposals) > _MAX_RESOLVED:
                _resolved_proposals = _resolved_proposals[:_MAX_RESOLVED]
            try:
                event_bus.publish(
                    "thought_action_proposal.resolved",
                    {"proposal_id": proposal_id, "decision": decision},
                )
            except Exception:
                pass
            return True

    return False


def get_pending_proposals() -> list[dict]:
    return list(_pending_proposals)


def build_proposal_surface() -> dict:
    return {
        "pending_proposals": list(_pending_proposals),
        "resolved_proposals": _resolved_proposals[:10],
        "pending_count": len(_pending_proposals),
        "needs_approval_count": sum(
            1 for p in _pending_proposals if p["proposal_type"] == "needs_approval"
        ),
    }
