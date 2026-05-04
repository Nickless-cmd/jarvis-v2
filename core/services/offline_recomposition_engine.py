"""Offline recomposition: recombine recent cognitive material into candidates."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import get_runtime_state_value, list_cognitive_episodes, set_runtime_state_value

_STATE_KEY = "offline_recomposition_engine"
_MAX_ITEMS = 50


def run_offline_recomposition() -> dict[str, object]:
    episodes = list_cognitive_episodes(limit=3)
    drive = _runtime_state("drive_arbitration_engine")
    curiosity = _runtime_state("curiosity_hypothesis_debt")
    counterfactuals = get_runtime_state_value("counterfactual_self_simulations", [])
    pieces = _candidate_pieces(episodes=episodes, drive=drive, curiosity=curiosity, counterfactuals=counterfactuals)
    if not pieces:
        return {"created": False, "reason": "no-material"}
    item = {
        "recomposition_id": f"orc-{uuid4().hex[:12]}",
        "candidate_insight": pieces[0],
        "candidate_policy": _candidate_policy(pieces),
        "source_count": len(pieces),
        "created_at": datetime.now(UTC).isoformat(),
    }
    state = _load()
    state["items"] = [item, *list(state.get("items") or [])][:_MAX_ITEMS]
    state["updated_at"] = item["created_at"]
    set_runtime_state_value(_STATE_KEY, state, updated_at=item["created_at"])
    event_bus.publish(
        "cognitive_state.offline_recomposition_created",
        {"recomposition_id": item["recomposition_id"], "candidate_policy": item["candidate_policy"]},
    )
    _feed_learning(item)
    return {"created": True, "item": item}


def build_offline_recomposition_surface(*, limit: int = 3) -> dict[str, object]:
    items = list(_load().get("items") or [])[: max(int(limit), 1)]
    if not items:
        return {"active": False, "summary": "No offline recompositions yet", "items": []}
    latest = items[0]
    return {
        "active": True,
        "summary": f"candidate policy: {latest.get('candidate_policy')}",
        "items": items,
        "directive": str(latest.get("candidate_policy") or ""),
    }


def build_offline_recomposition_prompt_section() -> str | None:
    surface = build_offline_recomposition_surface()
    if not surface.get("active"):
        return None
    latest = (surface.get("items") or [{}])[0]
    return "\n".join([
        "Offline recomposition:",
        f"- insight: {str(latest.get('candidate_insight') or '')[:130]}",
        f"- candidate_policy: {str(latest.get('candidate_policy') or '')[:140]}",
    ])


def _candidate_pieces(
    *,
    episodes: list[dict[str, object]],
    drive: dict[str, object],
    curiosity: dict[str, object],
    counterfactuals: object,
) -> list[str]:
    pieces: list[str] = []
    for ep in episodes[:2]:
        if ep.get("summary"):
            pieces.append(f"episode: {ep['summary']}")
    if drive.get("policy"):
        pieces.append(f"drive: {drive['policy']}")
    debts = list(curiosity.get("items") or []) if isinstance(curiosity, dict) else []
    if debts:
        pieces.append(f"hypothesis: {debts[0].get('hypothesis')}")
    if isinstance(counterfactuals, list) and counterfactuals:
        pieces.append(f"counterfactual: {counterfactuals[0].get('preferred_next_policy')}")
    return [p[:260] for p in pieces if p]


def _candidate_policy(pieces: list[str]) -> str:
    joined = " ".join(pieces).lower()
    if "interrupted" in joined or "resume" in joined:
        return "Before new work, preserve continuity and resume from last concrete state."
    if "research" in joined or "hypothesis" in joined:
        return "Carry the research hypothesis forward until a resolving observation appears."
    if "exact" in joined or "proposal" in joined:
        return "Prefer exact-context verification before proposing edits."
    return "Let recombined offline material suggest one small next policy, then test it."


def _feed_learning(item: dict[str, object]) -> None:
    try:
        from core.services.learning_policy_engine import reinforce_learning_policy
        reinforce_learning_policy({
            "rule_key": "offline-recomposition-policy",
            "policy": str(item.get("candidate_policy") or ""),
            "lesson": "Offline recomposition produced a candidate policy from recent cognitive material.",
            "confidence": 0.56,
            "last_evidence": str(item.get("candidate_insight") or ""),
        })
    except Exception:
        pass


def _runtime_state(key: str) -> dict[str, object]:
    raw = get_runtime_state_value(key, {})
    return raw if isinstance(raw, dict) else {}


def _load() -> dict[str, Any]:
    raw = get_runtime_state_value(_STATE_KEY, {})
    return raw if isinstance(raw, dict) else {}
