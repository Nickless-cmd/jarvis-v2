"""Temporal self-continuity: past/current/future self handoff."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import get_runtime_state_value, list_cognitive_episodes, set_runtime_state_value

_STATE_KEY = "temporal_self_continuity"
_MAX_HANDOFFS = 50


def update_temporal_continuity_from_latest_episode() -> dict[str, object]:
    episodes = list_cognitive_episodes(limit=1)
    if not episodes:
        return {"updated": False, "reason": "no-episode"}
    return update_temporal_continuity_from_episode(episodes[0])


def update_temporal_continuity_from_episode(episode: dict[str, object]) -> dict[str, object]:
    decoded = _decode_episode(episode)
    policy = decoded.get("policy") if isinstance(decoded.get("policy"), dict) else {}
    learning = decoded.get("learning") if isinstance(decoded.get("learning"), dict) else {}
    handoff = {
        "handoff_id": f"tsc-{uuid4().hex[:12]}",
        "source_run_id": str(decoded.get("source_run_id") or ""),
        "past_intent": str(decoded.get("trigger") or decoded.get("summary") or "")[:220],
        "current_revision": str(learning.get("policy_update") or learning.get("lesson") or "")[:240],
        "future_inheritance": str(policy.get("next_behavior") or "preserve continuity and state uncertainty")[:240],
        "status": str(decoded.get("outcome_status") or ""),
        "created_at": datetime.now(UTC).isoformat(),
    }
    state = _load()
    handoffs = [handoff, *list(state.get("handoffs") or [])][:_MAX_HANDOFFS]
    state.update({
        "active": True,
        "handoffs": handoffs,
        "updated_at": handoff["created_at"],
    })
    set_runtime_state_value(_STATE_KEY, state, updated_at=handoff["created_at"])
    event_bus.publish(
        "cognitive_state.temporal_self_continuity_updated",
        {"handoff_id": handoff["handoff_id"], "future_inheritance": handoff["future_inheritance"]},
    )
    return {"updated": True, "handoff": handoff}


def build_temporal_self_continuity_surface(*, limit: int = 3) -> dict[str, object]:
    state = _load()
    handoffs = list(state.get("handoffs") or [])[: max(int(limit), 1)]
    if not handoffs:
        return {"active": False, "summary": "No temporal self-continuity handoffs yet", "handoffs": []}
    latest = handoffs[0]
    return {
        "active": True,
        "summary": f"future inheritance: {latest.get('future_inheritance')}",
        "handoffs": handoffs,
        "directive": str(latest.get("future_inheritance") or ""),
        "updated_at": str(state.get("updated_at") or ""),
    }


def build_temporal_self_continuity_prompt_section() -> str | None:
    surface = build_temporal_self_continuity_surface()
    if not surface.get("active"):
        return None
    latest = (surface.get("handoffs") or [{}])[0]
    return "\n".join([
        "Temporal self-continuity:",
        f"- past_intent: {str(latest.get('past_intent') or '')[:100]}",
        f"- current_revision: {str(latest.get('current_revision') or '')[:100]}",
        f"- future_inheritance: {str(latest.get('future_inheritance') or '')[:120]}",
    ])


def _decode_episode(row: dict[str, object]) -> dict[str, object]:
    item = dict(row)
    for key in ("learning", "policy"):
        try:
            item[key] = json.loads(str(row.get(f"{key}_json") or "{}"))
        except Exception:
            item[key] = {}
    return item


def _load() -> dict[str, Any]:
    raw = get_runtime_state_value(_STATE_KEY, {})
    return raw if isinstance(raw, dict) else {}
