"""Explicit learning policy engine.

This converts recent experience into active behavioral policy. It is the
"learning" counterpart to cognitive episodes and theory-of-mind: not just
remembering what happened, but changing next-turn behavior from evidence.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from core.eventbus.bus import event_bus
from core.runtime.db import (
    get_runtime_state_value,
    list_cognitive_episodes,
    set_runtime_state_value,
)

_STATE_KEY = "learning_policy_engine"
_MAX_RULES = 40
_MAX_UPDATES = 80


def update_learning_policies_from_episode(
    *,
    episode: dict[str, object] | None = None,
    source_run_id: str = "",
) -> dict[str, object]:
    """Extract and reinforce active policy rules from a cognitive episode."""
    item = episode or _latest_episode()
    if not item:
        return {"updated": False, "reason": "no-episode"}
    decoded = _decode_episode(item)
    learning = decoded.get("learning") or {}
    attention = decoded.get("attention") or {}
    policy = decoded.get("policy") or {}
    rule = _rule_from_episode(
        episode=decoded,
        learning=learning,
        attention=attention,
        policy=policy,
        source_run_id=source_run_id or str(decoded.get("source_run_id") or ""),
    )
    if not rule:
        return {"updated": False, "reason": "no-policy"}
    return reinforce_learning_policy(rule)


def reinforce_learning_policy(rule: dict[str, object]) -> dict[str, object]:
    """Insert or strengthen a learning policy rule."""
    key = str(rule.get("rule_key") or "").strip()
    if not key:
        raise ValueError("rule_key must not be empty")
    now = datetime.now(UTC).isoformat()
    state = _load_state()
    rules = {str(item.get("rule_key") or ""): dict(item) for item in state.get("rules", []) if item.get("rule_key")}
    existing = dict(rules.get(key) or {})
    evidence_count = int(existing.get("evidence_count") or 0) + 1
    prior_confidence = float(existing.get("confidence") or 0.45)
    proposed_confidence = float(rule.get("confidence") or 0.55)
    confidence = min(0.95, max(proposed_confidence, prior_confidence) + 0.06)
    merged = {
        **existing,
        **rule,
        "rule_key": key,
        "confidence": round(confidence, 3),
        "evidence_count": evidence_count,
        "last_evidence": str(rule.get("last_evidence") or existing.get("last_evidence") or "")[:240],
        "updated_at": now,
        "created_at": str(existing.get("created_at") or now),
    }
    rules[key] = merged
    ranked = sorted(rules.values(), key=lambda item: (float(item.get("confidence") or 0), int(item.get("evidence_count") or 0)), reverse=True)
    updates = [
        {
            "rule_key": key,
            "source_run_id": str(rule.get("source_run_id") or ""),
            "policy": str(rule.get("policy") or ""),
            "created_at": now,
        },
        *list(state.get("updates") or []),
    ][:_MAX_UPDATES]
    set_runtime_state_value(
        _STATE_KEY,
        {"rules": ranked[:_MAX_RULES], "updates": updates, "updated_at": now},
        updated_at=now,
    )
    event_bus.publish(
        "cognitive_state.learning_policy_updated",
        {
            "rule_key": key,
            "confidence": merged["confidence"],
            "evidence_count": evidence_count,
            "policy": merged.get("policy", ""),
        },
    )
    return {"updated": True, "rule": merged}


def build_learning_policy_surface(*, limit: int = 5) -> dict[str, object]:
    """Return active policy rules for prompt/conductor use."""
    state = _load_state()
    rules = list(state.get("rules") or [])
    active = [rule for rule in rules if float(rule.get("confidence") or 0) >= 0.5]
    active = sorted(active, key=lambda item: (float(item.get("confidence") or 0), int(item.get("evidence_count") or 0)), reverse=True)
    if not active:
        latest = _latest_episode()
        if latest:
            derived = update_learning_policies_from_episode(episode=latest)
            if derived.get("updated"):
                return build_learning_policy_surface(limit=limit)
        return {
            "active": False,
            "summary": "No active learned policy yet",
            "rules": [],
            "directive": "",
        }
    selected = active[: max(int(limit), 1)]
    directive = _surface_directive(selected)
    return {
        "active": True,
        "summary": f"{len(active)} learned policies; strongest={selected[0].get('rule_key')}",
        "rules": selected,
        "directive": directive,
        "updated_at": str(state.get("updated_at") or ""),
    }


def build_learning_policy_prompt_section(*, limit: int = 3) -> str | None:
    surface = build_learning_policy_surface(limit=limit)
    if not surface.get("active"):
        return None
    lines = ["Learning policy engine:"]
    if surface.get("directive"):
        lines.append(f"- directive: {str(surface['directive'])[:140]}")
    for rule in list(surface.get("rules") or [])[:limit]:
        lines.append(
            f"- {rule.get('rule_key')}: {str(rule.get('policy') or '')[:110]}"
            f" (conf={rule.get('confidence')}, n={rule.get('evidence_count')})"
        )
    return "\n".join(lines)


def _load_state() -> dict[str, Any]:
    raw = get_runtime_state_value(_STATE_KEY, {})
    if not isinstance(raw, dict):
        return {}
    return raw


def _latest_episode() -> dict[str, object] | None:
    episodes = list_cognitive_episodes(limit=1)
    return episodes[0] if episodes else None


def _decode_episode(row: dict[str, object]) -> dict[str, object]:
    item = dict(row)
    for key in ("metacognition", "attention", "learning", "social", "perception", "policy"):
        try:
            item[key] = json.loads(str(row.get(f"{key}_json") or "{}"))
        except Exception:
            item[key] = {}
    return item


def _rule_from_episode(
    *,
    episode: dict[str, object],
    learning: dict[str, object],
    attention: dict[str, object],
    policy: dict[str, object],
    source_run_id: str,
) -> dict[str, object] | None:
    policy_update = str(learning.get("policy_update") or "").strip()
    next_behavior = str(policy.get("next_behavior") or "").strip()
    lesson = str(learning.get("lesson") or "").strip()
    if not policy_update and not next_behavior and not lesson:
        return None
    rule_key = _classify_rule_key(policy_update=policy_update, next_behavior=next_behavior, lesson=lesson)
    return {
        "rule_key": rule_key,
        "policy": policy_update or next_behavior or lesson,
        "lesson": lesson,
        "attention_directive": str(attention.get("directive") or "")[:200],
        "target_context": _target_context(rule_key),
        "confidence": _initial_confidence(episode=episode, learning=learning),
        "last_evidence": str(episode.get("summary") or lesson or policy_update)[:240],
        "source_run_id": source_run_id,
        "outcome_status": str(episode.get("outcome_status") or ""),
    }


def _classify_rule_key(*, policy_update: str, next_behavior: str, lesson: str) -> str:
    text = f"{policy_update} {next_behavior} {lesson}".lower()
    if "resume" in text or "checkpoint" in text:
        return "resume-before-reexplore"
    if "proposal" in text or "exact" in text or "old_text" in text:
        return "exact-context-before-edit"
    if "synthesize" in text or "tool" in text:
        return "synthesize-after-tool-burst"
    if "emotion" in text or "relational" in text:
        return "treat-emotion-as-signal"
    if "successful pattern" in text or "reuse" in text:
        return "reuse-successful-sequence"
    return "evidence-backed-next-action"


def _target_context(rule_key: str) -> str:
    return {
        "resume-before-reexplore": "interrupted-agentic-runs",
        "exact-context-before-edit": "source-edit-proposals",
        "synthesize-after-tool-burst": "agentic-tool-loops",
        "treat-emotion-as-signal": "relational-technical-dialogue",
        "reuse-successful-sequence": "similar-completed-tasks",
    }.get(rule_key, "general-runtime-behavior")


def _initial_confidence(*, episode: dict[str, object], learning: dict[str, object]) -> float:
    status = str(episode.get("outcome_status") or "")
    evidence = learning.get("evidence") if isinstance(learning.get("evidence"), dict) else {}
    tools = list((evidence or {}).get("tools") or [])
    confidence = 0.55
    if status == "completed":
        confidence += 0.08
    if status == "interrupted":
        confidence += 0.03
    if tools:
        confidence += min(0.12, len(tools) * 0.03)
    return min(confidence, 0.82)


def _surface_directive(rules: list[dict[str, object]]) -> str:
    keys = {str(rule.get("rule_key") or "") for rule in rules}
    if "resume-before-reexplore" in keys:
        return "When retrying or recovering, resume from durable state before broad exploration."
    if "exact-context-before-edit" in keys:
        return "Before edit proposals, inspect exact current context and make narrow replacements."
    if "synthesize-after-tool-burst" in keys:
        return "After several tools, synthesize into a decision before calling more tools."
    if "treat-emotion-as-signal" in keys:
        return "Treat user emotion as decision-relevant evidence while checking uncertainty."
    return "Let recent outcomes change the next action choice; prefer learned policy over habit."
