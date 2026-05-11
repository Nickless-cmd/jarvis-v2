"""Learning Pipeline Orchestrator — Phase 3 (Loop Closure).

Connects the six learning systems by routing outputs between them
during the heartbeat REFLECT phase (not as a separate daemon).

Routing rules:
  self_evaluation.completed
    → learning_policy_engine.reinforce_learning_policy()
    → reasoning_store.capture_conclusion()

  learning_policy.rule_created (confidence ≥ 0.7 + evidence ≥ 2)
    → policy_abstraction.abstract_rule()
    → reasoning_store.capture_conclusion()

  counterfactual.cycle_complete
    → agent_skill_distiller.distill_skills_for_role()
    → reasoning_store.capture_conclusion()

  agent_skill_distiller.completed
    → No further routing (skills in Agent Skill Library)

  agent_run.completed
    → agent_self_evaluation (implicit — already runs per tick)
    → reasoning_store.capture_conclusion()

Killswitch: 'learning_pipeline_enabled' setting in runtime.json
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from core.eventbus.bus import event_bus

logger = logging.getLogger(__name__)

_PIPELINE_ENABLED_KEY = "learning_pipeline_enabled"
_LOOKBACK_MINUTES = 60  # events from last 60 min
_MAX_ROUTE_PER_CYCLE = 10


def _now() -> str:
    return datetime.now(UTC).isoformat()


def is_enabled() -> bool:
    """Check killswitch."""
    try:
        from core.runtime.db import get_runtime_state_value
        return bool(get_runtime_state_value(_PIPELINE_ENABLED_KEY, True))
    except Exception:
        return True


def set_enabled(value: bool) -> None:
    """Toggle killswitch without restart."""
    from core.runtime.db import set_runtime_state_value
    set_runtime_state_value(_PIPELINE_ENABLED_KEY, value)


# ── Event queries ───────────────────────────────────────────────────────


def _recent_events(*, families: list[str], minutes: int = _LOOKBACK_MINUTES) -> list[dict[str, Any]]:
    """Fetch recent events from eventbus by family, ordered newest-first."""
    cutoff = (datetime.now(UTC) - timedelta(minutes=minutes)).isoformat()
    all_events: list[dict[str, Any]] = []
    for family in families:
        try:
            recent = event_bus.recent_by_family(family, limit=50)
            for ev in recent:
                created = str(ev.get("created_at", ""))
                if created >= cutoff:
                    all_events.append(ev)
        except Exception as exc:
            logger.debug("pipeline: event fetch failed for %s: %s", family, exc)

    # Dedup by event id, keep newest
    seen: set[int] = set()
    deduped: list[dict[str, Any]] = []
    for ev in sorted(all_events, key=lambda e: int(e.get("id", 0) or 0), reverse=True):
        eid = int(ev.get("id", 0) or 0)
        if eid and eid not in seen:
            seen.add(eid)
            deduped.append(ev)
    return deduped


# ── Route handlers ──────────────────────────────────────────────────────


def _route_self_evaluation(event: dict[str, Any]) -> list[dict[str, Any]]:
    """self_evaluation outcome → learning_policy + reasoning_store."""
    actions: list[dict[str, Any]] = []
    payload = event.get("payload") or {}
    summary = str(payload.get("summary") or event.get("summary") or "")

    if not summary:
        return actions

    # 1. Reinforce learning policy with evaluation insight
    try:
        from core.services.learning_policy_engine import reinforce_learning_policy

        rule = {
            "rule_key": f"self-eval-{event.get('id', 0)}",
            "policy": summary[:240],
            "lesson": summary[:240],
            "confidence": 0.55,
            "evidence_count": 1,
            "last_evidence": summary[:240],
            "target_context": "self-evaluation",
            "source_run_id": str(event.get("id", "")),
        }
        result = reinforce_learning_policy(rule)
        if result.get("updated"):
            actions.append({
                "action": "learning_policy.reinforced",
                "source": "self_evaluation",
                "rule_key": rule["rule_key"],
                "confidence": result.get("rule", {}).get("confidence", 0.55),
            })
    except Exception as exc:
        logger.debug("pipeline: self-eval → policy failed: %s", exc)

    # 2. Capture in reasoning store
    try:
        from core.services.reasoning_store import capture_conclusion

        cid = capture_conclusion(
            source="self_evaluation",
            conclusion_text=summary[:600],
            context="heartbeat self-evaluation cycle",
            confidence=0.5,
            source_record_id=str(event.get("id", "")),
        )
        if cid:
            actions.append({
                "action": "reasoning_store.captured",
                "conclusion_id": cid,
                "source": "self_evaluation",
            })
    except Exception as exc:
        logger.debug("pipeline: self-eval → reasoning_store failed: %s", exc)

    return actions


def _route_learning_policy_rule(event: dict[str, Any]) -> list[dict[str, Any]]:
    """learning_policy.rule_created (conf ≥ 0.7 + evidence ≥ 2) → abstraction + reasoning_store."""
    actions: list[dict[str, Any]] = []
    payload = event.get("payload") or {}
    confidence = float(payload.get("confidence") or 0.0)
    evidence_count = int(payload.get("evidence_count") or 0)

    if confidence < 0.7 or evidence_count < 2:
        return actions  # threshold not met

    rule_key = str(payload.get("rule_key") or "")
    policy = str(payload.get("policy") or "")
    if not rule_key or not policy:
        return actions

    # 1. Abstract the rule
    try:
        from core.services.policy_abstraction import abstract_rule

        result = abstract_rule(
            rule_key=rule_key,
            policy=policy,
            lesson=str(payload.get("lesson") or policy),
            target_context=str(payload.get("target_context") or "general-runtime-behavior"),
            evidence_count=evidence_count,
            confidence=confidence,
            source_domain=str(payload.get("target_context") or "general-runtime-behavior"),
        )
        if result.get("status") == "created":
            actions.append({
                "action": "policy_abstraction.generalized",
                "rule_key": rule_key,
                "policy_id": result.get("policy_id", ""),
                "generalized_principle": result.get("generalized_principle", "")[:120],
            })
    except Exception as exc:
        logger.debug("pipeline: policy → abstraction failed: %s", exc)

    # 2. Capture in reasoning store
    try:
        from core.services.reasoning_store import capture_conclusion

        cid = capture_conclusion(
            source="learning_policy",
            conclusion_text=f"Rule '{rule_key}': {policy[:500]}",
            context=f"confidence={confidence}, evidence={evidence_count}",
            confidence=confidence,
            source_record_id=str(event.get("id", "")),
        )
        if cid:
            actions.append({
                "action": "reasoning_store.captured",
                "conclusion_id": cid,
                "source": "learning_policy",
            })
    except Exception as exc:
        logger.debug("pipeline: policy → reasoning_store failed: %s", exc)

    return actions


def _route_counterfactual_cycle(event: dict[str, Any]) -> list[dict[str, Any]]:
    """counterfactual.cycle_complete → skill distiller + reasoning_store."""
    actions: list[dict[str, Any]] = []
    payload = event.get("payload") or {}

    # 1. Feed to skill distiller (for the 'default' role)
    cf_count = int(payload.get("counterfactuals_generated") or 0)
    if cf_count > 0:
        try:
            from core.services.agent_skill_distiller import distill_skills_for_role

            result = distill_skills_for_role("default", days=7)
            if result.get("status") == "ok" and int(result.get("appended", 0) or 0) > 0:
                actions.append({
                    "action": "skill_distiller.triggered",
                    "role": "default",
                    "appended": result.get("appended", 0),
                })
        except Exception as exc:
            logger.debug("pipeline: counterfactual → distiller failed: %s", exc)

    # 2. Capture cycle summary in reasoning store
    try:
        from core.services.reasoning_store import capture_conclusion

        summary = (
            f"Counterfactual cycle: {payload.get('counterfactuals_generated', 0)} generated, "
            f"{payload.get('promoted', 0)} promoted, "
            f"{payload.get('triggers_fetched', 0)} triggers"
        )
        cid = capture_conclusion(
            source="counterfactual",
            conclusion_text=summary[:600],
            context="counterfactual reflection cycle",
            confidence=0.6,
            source_record_id=str(event.get("id", "")),
        )
        if cid:
            actions.append({
                "action": "reasoning_store.captured",
                "conclusion_id": cid,
                "source": "counterfactual",
            })
    except Exception as exc:
        logger.debug("pipeline: counterfactual → reasoning_store failed: %s", exc)

    return actions


def _route_agent_run(event: dict[str, Any]) -> list[dict[str, Any]]:
    """agent_run.completed → reasoning_store."""
    actions: list[dict[str, Any]] = []
    payload = event.get("payload") or {}
    outcome = str(payload.get("outcome") or payload.get("summary") or "")

    if not outcome:
        return actions

    # Capture in reasoning store
    try:
        from core.services.reasoning_store import capture_conclusion

        cid = capture_conclusion(
            source="agent_run",
            conclusion_text=outcome[:600],
            context=f"agent role: {payload.get('role', 'unknown')}",
            confidence=0.5,
            source_record_id=str(payload.get("run_id") or event.get("id", "")),
        )
        if cid:
            actions.append({
                "action": "reasoning_store.captured",
                "conclusion_id": cid,
                "source": "agent_run",
            })
    except Exception as exc:
        logger.debug("pipeline: agent_run → reasoning_store failed: %s", exc)

    return actions


# ── Main orchestrator entry ─────────────────────────────────────────────


def run_pipeline(*, force: bool = False) -> dict[str, Any]:
    """Run one full pipeline routing cycle.

    Called from the heartbeat REFLECT phase (see heartbeat_phases.py).
    Queries recent events from all six systems and routes outputs
    to appropriate downstream inputs.

    Returns a summary dict suitable for eventbus publication and
    inclusion in the phased tick result.
    """
    if not is_enabled() and not force:
        return {"status": "skipped", "reason": "killswitch-off"}

    started_at = datetime.now(UTC)
    all_actions: list[dict[str, Any]] = []
    generalizations_created = 0
    reasoning_captured = 0
    policies_routed = 0

    # Fetch events from the six systems
    events = _recent_events(
        families=[
            "self_review",   # self_evaluation events
            "cognitive_state",  # learning_policy events
            "counterfactual",   # counterfactual events
            "agentic",         # agent_run events
        ],
        minutes=_LOOKBACK_MINUTES,
    )

    if not events:
        return {
            "status": "idle",
            "events_found": 0,
            "actions_taken": 0,
            "generalizations_created": 0,
            "reasoning_captured": 0,
            "policies_routed": 0,
            "elapsed_ms": 0,
            "cycle_at": _now(),
        }

    # Route each event (newest first, capped)
    routed = 0
    route_handlers = {
        "self_review": _route_self_evaluation,
        "cognitive_state": _route_learning_policy_rule,
        "counterfactual": _route_counterfactual_cycle,
        "agentic": _route_agent_run,
    }

    for event in events:
        if routed >= _MAX_ROUTE_PER_CYCLE:
            break

        family = str(event.get("family") or "")
        kind = str(event.get("kind") or "")
        handler = route_handlers.get(family)

        if handler is None:
            continue

        # For cognitive_state, only handle learning_policy_updated events
        if family == "cognitive_state" and "learning_policy_updated" not in kind:
            continue

        actions = handler(event)
        if actions:
            all_actions.extend(actions)
            routed += 1

            for a in actions:
                if a.get("action") == "policy_abstraction.generalized":
                    generalizations_created += 1
                elif a.get("action") == "reasoning_store.captured":
                    reasoning_captured += 1
                else:
                    policies_routed += 1

    elapsed_ms = int((datetime.now(UTC) - started_at).total_seconds() * 1000)

    result = {
        "status": "completed",
        "events_found": len(events),
        "events_routed": routed,
        "actions_taken": len(all_actions),
        "generalizations_created": generalizations_created,
        "reasoning_captured": reasoning_captured,
        "policies_routed": policies_routed,
        "actions": all_actions[:10],  # summary only
        "elapsed_ms": elapsed_ms,
        "cycle_at": _now(),
    }

    # Cleanup: sweep abstraction candidates if nothing else happened
    # This ensures we don't miss policies that were created between cycles
    if generalizations_created == 0 and reasoning_captured == 0:
        try:
            from core.services.policy_abstraction import sweep_abstraction_candidates
            swept = sweep_abstraction_candidates(max_rules=2)
            if swept:
                result["sweep_abstractions"] = len(swept)
                result["actions_taken"] += len(swept)
                result["generalizations_created"] += len(swept)
        except Exception:
            pass

    # Publish cycle summary
    try:
        event_bus.publish("learning_pipeline.cycle_completed", {
            "generalizations_created": generalizations_created,
            "reasoning_captured": reasoning_captured,
            "policies_routed": policies_routed,
            "events_found": len(events),
            "elapsed_ms": elapsed_ms,
        })
    except Exception:
        pass

    return result


def run_reflect_cycle() -> dict[str, Any]:
    """Thin wrapper for REFLECT phase integration.

    This is the only function called from heartbeat_phases.py.
    The REFLECT phase calls this after reflection synthesis.
    """
    if not is_enabled():
        return {"status": "skipped", "reason": "killswitch-off"}
    return run_pipeline()
