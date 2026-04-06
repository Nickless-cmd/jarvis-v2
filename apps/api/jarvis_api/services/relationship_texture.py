"""Relationship Texture — tracks the quality of the relationship over time.

Not just facts about the user, but HOW interactions flow:
humor, corrections, trust trajectory, inside references, unspoken rules.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import UTC, datetime

from core.eventbus.bus import event_bus
from core.runtime.db import (
    get_latest_cognitive_relationship_texture,
    upsert_cognitive_relationship_texture,
)

logger = logging.getLogger(__name__)

_CORRECTION_MARKERS = [
    "nej", "forkert", "ikke det", "det er stadig", "hold nu",
    "det virker ikke", "prøv igen", "forkert fil", "glem det",
    "det er ikke", "du har misforstået",
]

_HUMOR_MARKERS = [
    "haha", "lol", "😂", "😄", "sjovt", "godt fundet",
    "den var god", "humor",
]

_TRUST_POSITIVE = [
    "perfekt", "godt arbejde", "præcis", "fedt", "flot",
    "tak", "ja forsæt", "godkendt",
]


def update_relationship_from_run(
    *,
    run_id: str,
    user_message: str,
    assistant_response: str,
    outcome_status: str,
    turn_count: int = 1,
) -> dict[str, object] | None:
    """Analyze a run and update relationship texture."""
    current = get_latest_cognitive_relationship_texture()
    msg_lower = user_message.lower()

    # Parse current state
    humor_freq = float(current.get("humor_frequency", 0.0)) if current else 0.0
    inside_refs = _safe_json_list(current.get("inside_references") if current else None)
    corrections = _safe_json_list(current.get("correction_patterns") if current else None)
    trust_traj = _safe_json_list(current.get("trust_trajectory") if current else None)
    productive = _safe_json_dict(current.get("productive_hours") if current else None)
    conv_rhythm = _safe_json_dict(current.get("conversation_rhythm") if current else None)
    unspoken = _safe_json_list(current.get("unspoken_rules") if current else None)

    changed = False

    # Detect corrections
    is_correction = any(marker in msg_lower for marker in _CORRECTION_MARKERS)
    if is_correction:
        # Extract what they corrected (first 60 chars of their message)
        correction_note = user_message[:60].strip()
        if correction_note and correction_note not in corrections:
            corrections.append(correction_note)
            corrections = corrections[-15:]  # cap at 15
        changed = True

    # Detect humor
    has_humor = any(marker in msg_lower for marker in _HUMOR_MARKERS)
    if has_humor:
        humor_freq = min(1.0, humor_freq + 0.02)
        changed = True
    else:
        humor_freq = max(0.0, humor_freq - 0.005)  # slow decay

    # Trust trajectory
    trust_delta = 0.0
    if is_correction:
        trust_delta = -0.02
    elif any(marker in msg_lower for marker in _TRUST_POSITIVE):
        trust_delta = 0.01
    elif outcome_status in ("completed", "success"):
        trust_delta = 0.005

    if trust_delta != 0.0:
        current_trust = trust_traj[-1] if trust_traj else 0.5
        new_trust = max(0.0, min(1.0, current_trust + trust_delta))
        trust_traj.append(round(new_trust, 3))
        trust_traj = trust_traj[-50:]  # keep last 50
        changed = True

    # Productive hours tracking
    hour = datetime.now(UTC).hour
    hour_key = str(hour)
    productive[hour_key] = productive.get(hour_key, 0) + 1
    changed = True

    # Inside references — detect repeated unique phrases
    words = [w for w in msg_lower.split() if len(w) > 5]
    for word in words:
        # Crude: if a distinctive word appears and isn't common
        if word not in inside_refs and len(inside_refs) < 20:
            # Only add if it seems specific (appears again later)
            pass  # This will be enhanced with frequency tracking

    # Conversation rhythm
    if turn_count > 0:
        avg_turns = float(conv_rhythm.get("avg_turns", 0))
        count = int(conv_rhythm.get("session_count", 0))
        new_count = count + 1
        new_avg = ((avg_turns * count) + turn_count) / new_count
        conv_rhythm["avg_turns"] = round(new_avg, 1)
        conv_rhythm["session_count"] = new_count
        changed = True

    if not changed:
        return None

    result = upsert_cognitive_relationship_texture(
        humor_frequency=humor_freq,
        inside_references=json.dumps(inside_refs, ensure_ascii=False),
        correction_patterns=json.dumps(corrections, ensure_ascii=False),
        trust_trajectory=json.dumps(trust_traj, ensure_ascii=False),
        productive_hours=json.dumps(productive, ensure_ascii=False),
        conversation_rhythm=json.dumps(conv_rhythm, ensure_ascii=False),
        unspoken_rules=json.dumps(unspoken, ensure_ascii=False),
    )

    event_bus.publish(
        "cognitive_relationship.texture_updated",
        {"run_id": run_id, "trust_delta": trust_delta, "was_correction": is_correction},
    )
    return result


def update_relationship_async(**kwargs) -> None:
    threading.Thread(
        target=lambda: _safe(update_relationship_from_run, **kwargs),
        daemon=True,
    ).start()


def build_relationship_texture_surface() -> dict[str, object]:
    current = get_latest_cognitive_relationship_texture()
    if not current:
        return {"active": False, "current": None, "summary": "No relationship data yet"}
    trust_traj = _safe_json_list(current.get("trust_trajectory"))
    latest_trust = trust_traj[-1] if trust_traj else 0.5
    corrections = _safe_json_list(current.get("correction_patterns"))
    return {
        "active": True,
        "current": current,
        "summary": (
            f"v{current.get('version', 0)}, trust={latest_trust:.2f}, "
            f"{len(corrections)} corrections tracked"
        ),
    }


def _safe(fn, **kwargs):
    try:
        fn(**kwargs)
    except Exception:
        logger.debug("relationship_texture: failed", exc_info=True)


def _safe_json_list(value) -> list:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
    return []


def _safe_json_dict(value) -> dict:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
    return {}
