from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

from apps.api.jarvis_api.services.runtime_learning_signals import action_domain, action_family


DecisionMode = Literal["execute", "propose", "defer", "noop"]


@dataclass(slots=True)
class RuntimeDecisionInput:
    cognitive_frame: dict[str, Any]
    operational_memory: dict[str, Any]
    loop_runtime: dict[str, Any]
    initiative_state: dict[str, Any]
    visible_state: dict[str, Any]
    tool_intent_state: dict[str, Any]
    timestamp_iso: str


@dataclass(slots=True)
class RuntimeActionCandidate:
    action_id: str
    score: float
    reason: str
    payload: dict[str, Any]
    mode: DecisionMode


@dataclass(slots=True)
class RuntimeDecision:
    mode: DecisionMode
    action_id: str
    reason: str
    score: float
    payload: dict[str, Any]
    considered: list[dict[str, Any]]


def decide_next_action(inputs: RuntimeDecisionInput) -> RuntimeDecision:
    candidates = build_action_candidates(inputs)
    return choose_best_candidate(candidates)


def build_action_candidates(inputs: RuntimeDecisionInput) -> list[RuntimeActionCandidate]:
    visible_active = bool((inputs.visible_state.get("summary") or {}).get("active"))
    approval_pending = bool((inputs.tool_intent_state.get("summary") or {}).get("pending_count"))

    candidates: list[RuntimeActionCandidate] = []
    candidates.extend(_open_loop_candidates(inputs, visible_active=visible_active))
    candidates.extend(_initiative_candidates(inputs, visible_active=visible_active))
    candidates.extend(_memory_candidates(inputs, visible_active=visible_active))
    candidates.extend(
        _reflection_candidates(
            inputs,
            visible_active=visible_active,
            approval_pending=approval_pending,
        )
    )

    if not candidates:
        candidates.append(
            RuntimeActionCandidate(
                action_id="noop",
                score=0.0,
                reason="No bounded action candidates were available.",
                payload={},
                mode="noop",
            )
        )
    adjusted = [_apply_feedback(candidate, inputs) for candidate in candidates]
    return sorted(adjusted, key=lambda item: item.score, reverse=True)


def choose_best_candidate(candidates: list[RuntimeActionCandidate]) -> RuntimeDecision:
    if not candidates:
        return RuntimeDecision(
            mode="noop",
            action_id="noop",
            reason="No candidates were considered.",
            score=0.0,
            payload={},
            considered=[],
        )
    winner = candidates[0]
    return RuntimeDecision(
        mode=winner.mode,
        action_id=winner.action_id,
        reason=winner.reason,
        score=winner.score,
        payload=dict(winner.payload),
        considered=[asdict(candidate) for candidate in candidates],
    )


def _open_loop_candidates(
    inputs: RuntimeDecisionInput,
    *,
    visible_active: bool,
) -> list[RuntimeActionCandidate]:
    loops = list(inputs.operational_memory.get("open_loops") or [])
    if not loops:
        return []
    top_loop = loops[0]
    status = str(top_loop.get("runtime_status") or top_loop.get("status") or "active")
    title = str(top_loop.get("title") or top_loop.get("summary") or "Open loop").strip()
    candidates = [
        RuntimeActionCandidate(
            action_id="follow_open_loop",
            score=0.85,
            reason=f"Active open loop requires carry-forward: {title[:120]} ({status}).",
            payload={
                "loop_id": str(top_loop.get("loop_id") or ""),
                "title": title[:200],
                "status": status,
                "canonical_key": str(top_loop.get("canonical_key") or ""),
            },
            mode="propose" if visible_active else "execute",
        )
    ]
    if _looks_repo_focused(top_loop):
        candidates.append(
            RuntimeActionCandidate(
                action_id="inspect_repo_context",
                score=0.92 if not visible_active else 0.74,
                reason=f"Repo-focused open loop benefits from bounded repo inspection first: {title[:120]}.",
                payload={
                    "loop_id": str(top_loop.get("loop_id") or ""),
                    "title": title[:200],
                    "status": status,
                    "canonical_key": str(top_loop.get("canonical_key") or ""),
                    "focus": title[:200],
                },
                mode="execute" if not visible_active else "propose",
            )
        )
    return candidates


def _initiative_candidates(
    inputs: RuntimeDecisionInput,
    *,
    visible_active: bool,
) -> list[RuntimeActionCandidate]:
    initiatives = list(inputs.initiative_state.get("pending") or [])
    if not initiatives:
        return []
    top_initiative = initiatives[0]
    focus = str(top_initiative.get("focus") or "Pending initiative").strip()
    initiative_id = str(top_initiative.get("initiative_id") or "")
    return [
        RuntimeActionCandidate(
            action_id="promote_initiative_to_visible_lane",
            score=0.8 if visible_active else 0.7,
            reason=f"Queued initiative is waiting for bounded follow-up: {focus[:120]}.",
            payload={
                "initiative_id": initiative_id,
                "focus": focus[:200],
                "priority": str(top_initiative.get("priority") or "medium"),
            },
            mode="propose" if visible_active else "execute",
        )
    ]


def _memory_candidates(
    inputs: RuntimeDecisionInput,
    *,
    visible_active: bool,
) -> list[RuntimeActionCandidate]:
    summary = inputs.operational_memory.get("summary") or {}
    stale = bool(summary.get("memory_context_stale"))
    recent_outcomes = int(summary.get("recent_outcome_count") or 0)
    if not stale and recent_outcomes > 0:
        return []
    return [
        RuntimeActionCandidate(
            action_id="refresh_memory_context",
            score=0.55,
            reason="Operational memory context is thin or stale, so refresh before larger moves.",
            payload={"reason": "stale-operational-memory"},
            mode="propose" if visible_active else "execute",
        )
    ]


def _reflection_candidates(
    inputs: RuntimeDecisionInput,
    *,
    visible_active: bool,
    approval_pending: bool,
) -> list[RuntimeActionCandidate]:
    frame_summary = inputs.cognitive_frame.get("summary") or {}
    current_mode = str(frame_summary.get("current_mode") or inputs.cognitive_frame.get("current_mode") or "watch")
    contradiction_count = int((inputs.operational_memory.get("summary") or {}).get("contradiction_count") or 0)
    if approval_pending or contradiction_count > 0 or current_mode == "clarify":
        return [
            RuntimeActionCandidate(
                action_id="bounded_self_check",
                score=0.65,
                reason="Current state indicates clarification or contradiction pressure before action.",
                payload={
                    "current_mode": current_mode,
                    "contradiction_count": contradiction_count,
                },
                mode="execute",
            )
        ]
    if visible_active:
        return [
            RuntimeActionCandidate(
                action_id="propose_next_user_step",
                score=0.4,
                reason="Visible lane is active but no stronger autonomous move dominates.",
                payload={"current_mode": current_mode},
                mode="propose",
            )
        ]
    return [
        RuntimeActionCandidate(
            action_id="write_internal_work_note",
            score=0.35,
            reason="Quiet runtime state benefits from a small internal note rather than silence.",
            payload={
                "current_mode": current_mode,
                "reason": "quiet runtime state",
                "title": _top_open_loop_title(inputs),
            },
            mode="execute",
        )
    ]


def _looks_repo_focused(loop: dict[str, Any]) -> bool:
    haystack = " ".join(
        str(loop.get(key) or "")
        for key in ("title", "summary", "canonical_key", "reason_code", "loop_id")
    ).lower()
    return any(
        token in haystack
        for token in ("repo", "git", "working tree", "branch", "commit", "code", "workspace")
    )


def _apply_feedback(
    candidate: RuntimeActionCandidate,
    inputs: RuntimeDecisionInput,
) -> RuntimeActionCandidate:
    feedback_summary = dict(inputs.operational_memory.get("executive_feedback_summary") or {})
    action_stats = dict(feedback_summary.get("action_stats") or {})
    stats = dict(action_stats.get(candidate.action_id) or {})
    runtime_learning_summary = dict(inputs.operational_memory.get("runtime_learning_summary") or {})
    semantic_feedback = dict(inputs.operational_memory.get("semantic_feedback_summary") or {})
    signal_stats = dict(semantic_feedback.get("signal_stats") or {})
    latest_action = str(feedback_summary.get("latest_action") or "")
    latest_status = str(feedback_summary.get("latest_status") or "")
    note_synergy = _matching_note_loop_synergy(candidate, inputs)

    score = float(candidate.score)
    reasons = [candidate.reason]

    if latest_action == candidate.action_id and latest_status in {"executed", "proposed"}:
        score -= 0.14
        reasons.append(
            f"Recent feedback dampens repetition because {candidate.action_id} just ended as {latest_status}."
        )

    blocked_count = int(stats.get("blocked_count") or 0)
    failed_count = int(stats.get("failed_count") or 0)
    blocked_weight = float(stats.get("blocked_weight") or 0.0) or float(blocked_count)
    failed_weight = float(stats.get("failed_weight") or 0.0) or float(failed_count)
    no_change_count = int(stats.get("no_change_count") or 0)
    no_change_weight = float(stats.get("no_change_weight") or 0.0) or float(no_change_count)
    success_count = int(stats.get("success_count") or 0)
    success_weight = float(stats.get("success_weight") or 0.0) or float(success_count)
    if blocked_weight > 0:
        score -= min(0.22, 0.11 * blocked_weight)
        reasons.append(
            "Recent blocked feedback penalizes "
            f"{candidate.action_id} ({blocked_count} blocked outcome(s), weight={blocked_weight:.2f})."
        )
    if failed_weight > 0:
        score -= min(0.28, 0.14 * failed_weight)
        reasons.append(
            "Recent failed feedback penalizes "
            f"{candidate.action_id} ({failed_count} failed outcome(s), weight={failed_weight:.2f})."
        )
    if no_change_weight > 0 and candidate.action_id == "inspect_repo_context":
        score -= min(0.26, 0.18 * no_change_weight)
        reasons.append(
            "Outcome learning lowers repo inspection baseline because recent inspections "
            f"kept finding nothing new ({no_change_count} no-change outcome(s), weight={no_change_weight:.2f})."
        )
    if success_weight > 0 and candidate.action_id == "refresh_memory_context":
        score -= min(0.12, 0.06 * success_weight)
        reasons.append(
            "Memory refresh already succeeded recently, so refresh is temporarily deprioritized."
        )
    if success_weight > 0 and candidate.action_id == "bounded_self_check":
        score -= min(0.10, 0.05 * success_weight)
        reasons.append(
            "A recent bounded self-check already ran, so repeating it immediately is less valuable."
        )
    if note_synergy is not None and candidate.action_id == "follow_open_loop":
        synergy_boost = min(0.18, float(note_synergy.get("match_score") or 0.0))
        if synergy_boost > 0:
            score += synergy_boost
            reasons.append(
                "Recent persisted work note reinforces this loop "
                f"via matched terms {list(note_synergy.get('matched_terms') or [])[:4]}."
            )
    score, family_reasons = _apply_persistent_learning(candidate, runtime_learning_summary, score=score)
    reasons.extend(family_reasons)
    score, semantic_reasons = _apply_semantic_feedback(
        candidate,
        inputs,
        score=score,
        signal_stats=signal_stats,
    )
    reasons.extend(semantic_reasons)

    return RuntimeActionCandidate(
        action_id=candidate.action_id,
        score=max(score, 0.0),
        reason=" ".join(reasons),
        payload=dict(candidate.payload),
        mode=candidate.mode,
    )


def _matching_note_loop_synergy(
    candidate: RuntimeActionCandidate,
    inputs: RuntimeDecisionInput,
) -> dict[str, Any] | None:
    if candidate.action_id != "follow_open_loop":
        return None
    loop_id = str(candidate.payload.get("loop_id") or "")
    canonical_key = str(candidate.payload.get("canonical_key") or "")
    title = str(candidate.payload.get("title") or "")
    for item in list(inputs.operational_memory.get("note_loop_synergies") or []):
        if loop_id and str(item.get("loop_id") or "") == loop_id:
            return dict(item)
        if canonical_key and str(item.get("canonical_key") or "") == canonical_key:
            return dict(item)
        if title and str(item.get("title") or "") == title:
            return dict(item)
    return None


def _top_open_loop_title(inputs: RuntimeDecisionInput) -> str:
    loops = list(inputs.operational_memory.get("open_loops") or [])
    if not loops:
        return ""
    top_loop = loops[0]
    return str(top_loop.get("title") or top_loop.get("summary") or "").strip()[:200]


def _apply_semantic_feedback(
    candidate: RuntimeActionCandidate,
    inputs: RuntimeDecisionInput,
    *,
    score: float,
    signal_stats: dict[str, dict[str, Any]],
) -> tuple[float, list[str]]:
    reasons: list[str] = []
    adjusted = float(score)

    task_created = _signal_weight(signal_stats, "task_created")
    note_persisted = _signal_weight(signal_stats, "note_persisted")
    repo_change = _signal_weight(signal_stats, "repo_actionable_change")
    repo_blocked = _signal_weight(signal_stats, "repo_capability_blocked")
    visible_proposal = _signal_weight(signal_stats, "visible_proposal_made")

    if candidate.action_id == "follow_open_loop" and task_created > 0:
        adjusted -= min(0.16, 0.10 * task_created)
        reasons.append(
            "Recent runtime-task-created feedback reduces immediate loop repetition "
            f"(weight={task_created:.2f})."
        )
    if candidate.action_id == "write_internal_work_note" and note_persisted > 0:
        adjusted -= min(0.12, 0.07 * note_persisted)
        reasons.append(
            "Recent note persistence lowers the value of writing another internal note immediately "
            f"(weight={note_persisted:.2f})."
        )
    if candidate.action_id == "write_internal_work_note" and task_created > 0:
        adjusted -= min(0.08, 0.05 * task_created)
        reasons.append(
            "A recently created runtime task already externalized work, so another note is less useful right now."
        )
    if (
        candidate.action_id == "follow_open_loop"
        and _candidate_is_repo_focused(candidate)
        and repo_change > 0
    ):
        adjusted += min(0.14, 0.08 * repo_change)
        reasons.append(
            "Recent repo inspection surfaced actionable change, so carrying the loop forward is more timely "
            f"(weight={repo_change:.2f})."
        )
    if candidate.action_id == "propose_next_user_step" and repo_blocked > 0:
        adjusted += min(0.12, 0.08 * repo_blocked)
        reasons.append(
            "Recent repo capability blocking shifts value toward a visible next-step proposal "
            f"(weight={repo_blocked:.2f})."
        )
    if candidate.action_id == "propose_next_user_step" and visible_proposal > 0:
        adjusted -= min(0.10, 0.06 * visible_proposal)
        reasons.append(
            "A recent visible proposal already went out, so repeating that move is slightly deprioritized."
        )
    return adjusted, reasons


def _apply_persistent_learning(
    candidate: RuntimeActionCandidate,
    runtime_learning_summary: dict[str, Any],
    *,
    score: float,
) -> tuple[float, list[str]]:
    reasons: list[str] = []
    adjusted = float(score)
    family = action_family(candidate.action_id)
    domain = _candidate_learning_domain(candidate)
    domain_stats = dict((runtime_learning_summary.get("domain_signal_stats") or {}).get(domain) or {})
    family_stats = dict((runtime_learning_summary.get("family_signal_stats") or {}).get(family) or {})
    action_stats = dict((runtime_learning_summary.get("action_signal_stats") or {}).get(candidate.action_id) or {})

    domain_blocked = _signal_weight(domain_stats, "family_blocked")
    domain_failed = _signal_weight(domain_stats, "family_failed")
    domain_no_change = _signal_weight(domain_stats, "family_no_change")
    domain_succeeded = _signal_weight(domain_stats, "family_succeeded")
    family_blocked = _signal_weight(family_stats, "family_blocked")
    family_failed = _signal_weight(family_stats, "family_failed")
    family_no_change = _signal_weight(family_stats, "family_no_change")
    family_succeeded = _signal_weight(family_stats, "family_succeeded")
    action_no_change = _signal_weight(action_stats, "action_no_change")

    if domain_blocked > 0:
        adjusted -= min(0.14, 0.08 * domain_blocked)
        reasons.append(
            f"Persistent domain-level blocking dampens this exact context ({domain}, weight={domain_blocked:.2f})."
        )
    if domain_failed > 0:
        adjusted -= min(0.16, 0.09 * domain_failed)
        reasons.append(
            f"Persistent domain-level failures dampen this exact context ({domain}, weight={domain_failed:.2f})."
        )
    if domain_no_change > 0 and candidate.action_id == "inspect_repo_context":
        adjusted -= min(0.14, 0.08 * domain_no_change)
        reasons.append(
            f"Persistent domain no-change learning keeps this repo context conservative ({domain}, weight={domain_no_change:.2f})."
        )
    if domain_succeeded > 0 and candidate.action_id in {"follow_open_loop", "propose_next_user_step"}:
        adjusted += min(0.10, 0.05 * domain_succeeded)
        reasons.append(
            f"Persistent domain success slightly boosts this exact context ({domain}, weight={domain_succeeded:.2f})."
        )
    if family_blocked > 0:
        adjusted -= min(0.16, 0.08 * family_blocked)
        reasons.append(
            f"Persistent family-level blocking dampens similar {family} actions (weight={family_blocked:.2f})."
        )
    if family_failed > 0:
        adjusted -= min(0.18, 0.09 * family_failed)
        reasons.append(
            f"Persistent family-level failures dampen similar {family} actions (weight={family_failed:.2f})."
        )
    if family_no_change > 0 and candidate.action_id == "inspect_repo_context":
        adjusted -= min(0.12, 0.07 * family_no_change)
        reasons.append(
            f"Persistent repo no-change learning keeps similar {family} actions conservative (weight={family_no_change:.2f})."
        )
    if action_no_change > 0 and candidate.action_id == "inspect_repo_context":
        adjusted -= min(0.12, 0.08 * action_no_change)
        reasons.append(
            "Persistent action-level no-change learning further lowers this exact repo inspection."
        )
    if family_succeeded > 0 and candidate.action_id in {"follow_open_loop", "propose_next_user_step"}:
        adjusted += min(0.08, 0.04 * family_succeeded)
        reasons.append(
            f"Persistent family success slightly boosts similar {family} actions (weight={family_succeeded:.2f})."
        )

    return adjusted, reasons


def _signal_weight(signal_stats: dict[str, dict[str, Any]], signal: str) -> float:
    bucket = dict(signal_stats.get(signal) or {})
    return float(bucket.get("weight") or bucket.get("count") or 0.0)


def _candidate_is_repo_focused(candidate: RuntimeActionCandidate) -> bool:
    haystack = " ".join(
        str(candidate.payload.get(key) or "")
        for key in ("title", "focus", "canonical_key", "loop_id")
    ).lower()
    return any(
        token in haystack
        for token in ("repo", "git", "working tree", "branch", "commit", "code", "workspace")
    )


def _candidate_learning_domain(candidate: RuntimeActionCandidate) -> str:
    return action_domain(
        action_id=candidate.action_id,
        outcome={
            "payload": dict(candidate.payload),
            "result": {},
        },
    )
