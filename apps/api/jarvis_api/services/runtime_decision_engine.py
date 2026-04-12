from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal


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
            payload={"current_mode": current_mode, "reason": "quiet runtime state"},
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
    latest_action = str(feedback_summary.get("latest_action") or "")
    latest_status = str(feedback_summary.get("latest_status") or "")

    score = float(candidate.score)
    reasons = [candidate.reason]

    if latest_action == candidate.action_id and latest_status in {"executed", "proposed"}:
        score -= 0.14
        reasons.append(
            f"Recent feedback dampens repetition because {candidate.action_id} just ended as {latest_status}."
        )

    blocked_count = int(stats.get("blocked_count") or 0)
    failed_count = int(stats.get("failed_count") or 0)
    if blocked_count > 0:
        score -= min(0.22, 0.11 * blocked_count)
        reasons.append(
            f"Recent blocked feedback penalizes {candidate.action_id} ({blocked_count} blocked outcome(s))."
        )
    if failed_count > 0:
        score -= min(0.28, 0.14 * failed_count)
        reasons.append(
            f"Recent failed feedback penalizes {candidate.action_id} ({failed_count} failed outcome(s))."
        )

    success_count = int(stats.get("success_count") or 0)
    if success_count > 0 and candidate.action_id == "refresh_memory_context":
        score -= min(0.12, 0.06 * success_count)
        reasons.append(
            "Memory refresh already succeeded recently, so refresh is temporarily deprioritized."
        )
    if success_count > 0 and candidate.action_id == "bounded_self_check":
        score -= min(0.10, 0.05 * success_count)
        reasons.append(
            "A recent bounded self-check already ran, so repeating it immediately is less valuable."
        )

    return RuntimeActionCandidate(
        action_id=candidate.action_id,
        score=max(score, 0.0),
        reason=" ".join(reasons),
        payload=dict(candidate.payload),
        mode=candidate.mode,
    )
