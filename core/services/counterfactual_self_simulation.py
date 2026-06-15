"""Counterfactual self-simulation for post-run learning.

This gives Jarvis a small "I could have done otherwise" primitive. It compares
the actual episode with nearby alternatives and feeds the preferred next policy
back into learning.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import get_runtime_state_value, list_cognitive_episodes, set_runtime_state_value

_STATE_KEY = "counterfactual_self_simulations"
_MAX_RECORDS = 60


def simulate_from_latest_episode() -> dict[str, object]:
    episodes = list_cognitive_episodes(limit=1)
    if not episodes:
        return {"created": False, "reason": "no-episode"}
    return simulate_from_episode(episodes[0])


def simulate_from_episode(episode: dict[str, object]) -> dict[str, object]:
    decoded = _decode_episode(episode)
    actual = _actual_action(decoded)
    alternatives = _alternatives_for_episode(decoded)
    preferred = _preferred_policy(decoded, alternatives)
    sim = {
        "simulation_id": f"cfs-{uuid4().hex[:12]}",
        "source_run_id": str(decoded.get("source_run_id") or ""),
        "episode_id": str(decoded.get("episode_id") or ""),
        "actual": actual,
        "alternatives": alternatives,
        "preferred_next_policy": preferred,
        "confidence": _confidence(decoded, alternatives),
        "created_at": datetime.now(UTC).isoformat(),
    }
    _save_simulation(sim)
    event_bus.publish(
        "cognitive_state.counterfactual_simulated",
        {
            "simulation_id": sim["simulation_id"],
            "source_run_id": sim["source_run_id"],
            "preferred_next_policy": preferred,
        },
    )
    # Generalized-learning capture (#159, plan A): den foretrukne next-policy er
    # en kontrafaktisk konklusion → fodr den ind i reasoning_store. dedup på episode.
    try:
        from core.services.reasoning_store import capture_conclusion
        _conf = {"high": 0.8, "medium": 0.5, "low": 0.3}.get(
            str(sim.get("confidence") or "").lower(), 0.4)
        capture_conclusion(
            source="counterfactual",
            conclusion_text=f"foretrukken next-policy: {preferred}"[:600],
            context=f"counterfactual af run {sim['source_run_id']}"[:200],
            confidence=_conf,
            dedup_key=f"counterfactual:{sim['source_run_id']}:{sim['episode_id']}",
        )
    except Exception:
        pass
    _feed_learning(sim)
    return {"created": True, "simulation": sim}


def build_counterfactual_surface(*, limit: int = 3) -> dict[str, object]:
    records = _load_records()[: max(int(limit), 1)]
    if not records:
        return {"active": False, "summary": "No counterfactual simulations yet", "simulations": []}
    latest = records[0]
    return {
        "active": True,
        "summary": f"latest preferred policy: {latest.get('preferred_next_policy')}",
        "simulations": records,
        "directive": str(latest.get("preferred_next_policy") or ""),
    }


def build_counterfactual_prompt_section(*, limit: int = 2) -> str | None:
    surface = build_counterfactual_surface(limit=limit)
    if not surface.get("active"):
        return None
    lines = ["Counterfactual self-simulation:"]
    if surface.get("directive"):
        lines.append(f"- preferred policy: {str(surface['directive'])[:140]}")
    for sim in list(surface.get("simulations") or [])[:limit]:
        alternatives = list(sim.get("alternatives") or [])
        best = alternatives[0] if alternatives else {}
        lines.append(
            f"- actual={str(sim.get('actual') or '')[:70]} | "
            f"nearby_alternative={str(best.get('action') or '')[:70]}"
        )
    return "\n".join(lines)


def _decode_episode(row: dict[str, object]) -> dict[str, object]:
    item = dict(row)
    for key in ("metacognition", "attention", "learning", "social", "perception", "policy"):
        try:
            item[key] = json.loads(str(row.get(f"{key}_json") or "{}"))
        except Exception:
            item[key] = {}
    return item


def _actual_action(episode: dict[str, object]) -> str:
    summary = str(episode.get("summary") or "").strip()
    status = str(episode.get("outcome_status") or "").strip()
    if summary:
        return f"{status}: {summary}"[:220]
    return status or "unknown action"


def _alternatives_for_episode(episode: dict[str, object]) -> list[dict[str, object]]:
    status = str(episode.get("outcome_status") or "")
    learning = episode.get("learning") if isinstance(episode.get("learning"), dict) else {}
    attention = episode.get("attention") if isinstance(episode.get("attention"), dict) else {}
    summary = str(episode.get("summary") or "").lower()
    alternatives: list[dict[str, object]] = []
    if status == "interrupted" or "interrupted" in summary or "timeout" in summary:
        alternatives.append({
            "action": "resume from checkpoint before new exploration",
            "predicted_outcome": "less lost context, faster recovery",
            "tradeoff": "may preserve stale assumptions unless rechecked",
        })
    if "proposal" in summary or "edit" in summary:
        alternatives.append({
            "action": "read exact file context before proposing edit",
            "predicted_outcome": "fewer proposal mismatches",
            "tradeoff": "one extra tool call",
        })
    if attention.get("directive"):
        alternatives.append({
            "action": str(attention["directive"])[:160],
            "predicted_outcome": "attention follows the latest salient signal",
            "tradeoff": "could overweight recent signal",
        })
    if learning.get("policy_update"):
        alternatives.append({
            "action": str(learning["policy_update"])[:160],
            "predicted_outcome": "next run changes behavior from evidence",
            "tradeoff": "policy may be overfit until reinforced",
        })
    alternatives.append({
        "action": "ask a clarifying question before acting",
        "predicted_outcome": "higher alignment when uncertainty is social or ambiguous",
        "tradeoff": "slower progress",
    })
    return alternatives[:4]


def _preferred_policy(episode: dict[str, object], alternatives: list[dict[str, object]]) -> str:
    policy = episode.get("policy") if isinstance(episode.get("policy"), dict) else {}
    if policy.get("next_behavior"):
        return str(policy["next_behavior"])[:220]
    if alternatives:
        return str(alternatives[0].get("action") or "")[:220]
    return "choose the lowest-regret next action and state uncertainty"


def _confidence(episode: dict[str, object], alternatives: list[dict[str, object]]) -> str:
    if str(episode.get("outcome_status") or "") == "completed" and alternatives:
        return "medium-high"
    if alternatives:
        return "medium"
    return "low"


def _load_records() -> list[dict[str, Any]]:
    raw = get_runtime_state_value(_STATE_KEY, [])
    return list(raw) if isinstance(raw, list) else []


def _save_simulation(sim: dict[str, object]) -> None:
    records = [sim, *_load_records()][:_MAX_RECORDS]
    set_runtime_state_value(_STATE_KEY, records, updated_at=str(sim["created_at"]))


def _feed_learning(sim: dict[str, object]) -> None:
    try:
        from core.services.learning_policy_engine import reinforce_learning_policy
        reinforce_learning_policy({
            "rule_key": "counterfactual-preferred-policy",
            "policy": str(sim.get("preferred_next_policy") or ""),
            "lesson": "Counterfactual simulation selected a lower-regret nearby policy.",
            "confidence": 0.6,
            "last_evidence": str(sim.get("actual") or ""),
            "source_run_id": str(sim.get("source_run_id") or ""),
        })
    except Exception:
        pass
