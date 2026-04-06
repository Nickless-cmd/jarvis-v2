"""Dream Carry-Over — hypotheses that survive across sessions.

Extends V2's existing dream_hypothesis_signals + dream_adoption_candidate.
When a dream is "adopted", it gets injected into the next visible prompt.
Confirmation in conversation → confidence up. Disconfirmation → archive.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from core.eventbus.bus import event_bus

logger = logging.getLogger(__name__)

_ACTIVE_DREAMS: list[dict[str, object]] = []
_DREAM_ARCHIVE: list[dict[str, object]] = []


def adopt_dream(
    *,
    dream_id: str,
    content: str,
    confidence: float = 0.5,
    source_memories: list[str] | None = None,
) -> dict[str, object]:
    """Adopt a dream hypothesis for carry-over to next session."""
    dream = {
        "dream_id": dream_id,
        "content": content[:300],
        "confidence": round(min(1.0, max(0.1, confidence)), 2),
        "source_memories": source_memories or [],
        "status": "active",
        "presented": False,
        "confirmed": False,
        "adopted_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }

    # Replace if exists
    _ACTIVE_DREAMS[:] = [d for d in _ACTIVE_DREAMS if d["dream_id"] != dream_id]
    _ACTIVE_DREAMS.append(dream)

    event_bus.publish(
        "cognitive_state.dream_adopted",
        {"dream_id": dream_id, "confidence": confidence},
    )
    return dream


def get_presentable_dream() -> dict[str, object] | None:
    """Get the highest-confidence un-presented dream for prompt injection."""
    unpresented = [d for d in _ACTIVE_DREAMS if not d.get("presented") and d.get("status") == "active"]
    if not unpresented:
        return None
    # Sort by confidence, highest first
    unpresented.sort(key=lambda d: d.get("confidence", 0), reverse=True)
    return unpresented[0]


def mark_dream_presented(dream_id: str) -> None:
    """Mark a dream as presented in the current session."""
    for d in _ACTIVE_DREAMS:
        if d["dream_id"] == dream_id:
            d["presented"] = True


def confirm_dream(dream_id: str) -> None:
    """Confirm a dream hypothesis — boost confidence."""
    for d in _ACTIVE_DREAMS:
        if d["dream_id"] == dream_id:
            d["confirmed"] = True
            d["confidence"] = min(1.0, d.get("confidence", 0.5) + 0.15)
            event_bus.publish(
                "cognitive_state.dream_confirmed",
                {"dream_id": dream_id},
            )


def reject_dream(dream_id: str) -> None:
    """Reject a dream hypothesis — archive with "was_wrong"."""
    for d in _ACTIVE_DREAMS:
        if d["dream_id"] == dream_id:
            d["status"] = "was_wrong"
            _DREAM_ARCHIVE.append(d)
            event_bus.publish(
                "cognitive_state.dream_rejected",
                {"dream_id": dream_id},
            )
    _ACTIVE_DREAMS[:] = [d for d in _ACTIVE_DREAMS if d["dream_id"] != dream_id]


def promote_confirmed_dream_to_identity(dream_id: str) -> dict[str, object] | None:
    """Promote a high-confidence confirmed dream to identity evolution proposal."""
    dream = next((d for d in _ACTIVE_DREAMS if d["dream_id"] == dream_id), None)
    if not dream or not dream.get("confirmed"):
        return None
    if float(dream.get("confidence", 0)) < 0.7:
        return None
    try:
        from apps.api.jarvis_api.services.contract_evolution import propose_identity_change
        return propose_identity_change(
            target_file="IDENTITY.md",
            proposed_addition=f"Bekræftet indsigt: {dream.get('content', '')[:200]}",
            rationale=f"Dream {dream_id} bekræftet med confidence {dream.get('confidence', 0):.1f}",
            confidence=float(dream.get("confidence", 0.7)),
        )
    except Exception:
        return None


def format_dream_for_prompt(dream: dict[str, object]) -> str:
    """Format a dream for injection into the visible prompt."""
    content = str(dream.get("content") or "")[:200]
    confidence = float(dream.get("confidence", 0.5))
    return f'[DREAM: "{content}" (confidence: {confidence:.1f})]'


def build_dream_carry_over_surface() -> dict[str, object]:
    confirmed = [d for d in _ACTIVE_DREAMS if d.get("confirmed")]
    wrong = [d for d in _DREAM_ARCHIVE if d.get("status") == "was_wrong"]
    return {
        "active": bool(_ACTIVE_DREAMS),
        "active_dreams": _ACTIVE_DREAMS,
        "archive": _DREAM_ARCHIVE[-10:],
        "confirmed_count": len(confirmed),
        "wrong_count": len(wrong),
        "summary": (
            f"{len(_ACTIVE_DREAMS)} active, {len(confirmed)} confirmed, {len(wrong)} wrong"
            if _ACTIVE_DREAMS else "No active dreams"
        ),
    }
