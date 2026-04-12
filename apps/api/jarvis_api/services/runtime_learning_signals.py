from __future__ import annotations

from typing import Any


ACTION_FAMILIES: dict[str, str] = {
    "refresh_memory_context": "memory_maintenance",
    "follow_open_loop": "loop_progression",
    "inspect_repo_context": "repo_observation",
    "review_recent_conversations": "conversation_observation",
    "write_internal_work_note": "internal_reflection",
    "bounded_self_check": "internal_reflection",
    "propose_next_user_step": "visible_prompting",
    "promote_initiative_to_visible_lane": "visible_prompting",
}


def action_family(action_id: str) -> str:
    return ACTION_FAMILIES.get(str(action_id or "").strip(), "generic")


def extract_runtime_learning_signals(outcome: dict[str, Any]) -> list[dict[str, Any]]:
    action_id = str(outcome.get("action_id") or "").strip()
    family = action_family(action_id)
    outcome_id = str(outcome.get("outcome_id") or "").strip()
    recorded_at = str(outcome.get("recorded_at") or "").strip()
    result_status = str(outcome.get("result_status") or "").strip()

    signals: list[dict[str, Any]] = []
    if result_status == "blocked":
        signals.extend(
            [
                _signal(
                    outcome_id=outcome_id,
                    source_action_id=action_id,
                    target_action_id=action_id,
                    signal_key="action_blocked",
                    weight=1.0,
                    recorded_at=recorded_at,
                ),
                _signal(
                    outcome_id=outcome_id,
                    source_action_id=action_id,
                    target_family=family,
                    signal_key="family_blocked",
                    weight=0.9,
                    recorded_at=recorded_at,
                ),
            ]
        )
    if result_status == "failed":
        signals.extend(
            [
                _signal(
                    outcome_id=outcome_id,
                    source_action_id=action_id,
                    target_action_id=action_id,
                    signal_key="action_failed",
                    weight=1.0,
                    recorded_at=recorded_at,
                ),
                _signal(
                    outcome_id=outcome_id,
                    source_action_id=action_id,
                    target_family=family,
                    signal_key="family_failed",
                    weight=0.9,
                    recorded_at=recorded_at,
                ),
            ]
        )
    if result_status in {"executed", "proposed"}:
        signals.append(
            _signal(
                outcome_id=outcome_id,
                source_action_id=action_id,
                target_family=family,
                signal_key="family_succeeded",
                weight=0.6,
                recorded_at=recorded_at,
            )
        )
    if _outcome_looks_like_no_change(outcome):
        signals.extend(
            [
                _signal(
                    outcome_id=outcome_id,
                    source_action_id=action_id,
                    target_action_id=action_id,
                    signal_key="action_no_change",
                    weight=0.8,
                    recorded_at=recorded_at,
                ),
                _signal(
                    outcome_id=outcome_id,
                    source_action_id=action_id,
                    target_family=family,
                    signal_key="family_no_change",
                    weight=0.7,
                    recorded_at=recorded_at,
                ),
            ]
        )

    semantic_signals = _extract_semantic_signals(outcome)
    for signal_key, target_family, weight in semantic_signals:
        signals.append(
            _signal(
                outcome_id=outcome_id,
                source_action_id=action_id,
                target_family=target_family,
                signal_key=signal_key,
                weight=weight,
                recorded_at=recorded_at,
            )
        )

    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for item in signals:
        key = (
            str(item.get("source_action_id") or ""),
            str(item.get("target_action_id") or ""),
            str(item.get("target_family") or ""),
            str(item.get("signal_key") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _signal(
    *,
    outcome_id: str,
    source_action_id: str,
    signal_key: str,
    weight: float,
    recorded_at: str,
    target_action_id: str = "",
    target_family: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "outcome_id": outcome_id,
        "source_action_id": source_action_id,
        "target_action_id": target_action_id,
        "target_family": target_family,
        "signal_key": signal_key,
        "signal_weight": float(weight),
        "signal_count": 1,
        "metadata": dict(metadata or {}),
        "recorded_at": recorded_at,
    }


def _extract_semantic_signals(outcome: dict[str, Any]) -> list[tuple[str, str, float]]:
    result = outcome.get("result") or outcome.get("result_json") or {}
    details = result.get("details") if isinstance(result, dict) else {}
    side_effects = list(result.get("side_effects") or []) if isinstance(result, dict) else []
    summary = str(outcome.get("result_summary") or "")
    haystack = " ".join(str(part) for part in (summary, details, side_effects, result)).lower()

    signals: list[tuple[str, str, float]] = []
    side_effect_list = [str(effect or "").strip() for effect in side_effects]
    if "runtime-task-created" in side_effect_list:
        signals.append(("task_created", "loop_progression", 1.0))
        signals.append(("task_created", "internal_reflection", 0.7))
    if "visible-work-note-persisted" in side_effect_list or "internal-work-note" in side_effect_list:
        signals.append(("note_persisted", "internal_reflection", 1.0))
    if "repo-context-inspected" in side_effect_list:
        signals.append(("repo_context_inspected", "repo_observation", 1.0))
    if "workspace-capability-blocked" in side_effect_list:
        signals.append(("repo_capability_blocked", "visible_prompting", 1.0))
    if "visible-proposal" in side_effect_list or "initiative-promoted" in side_effect_list:
        signals.append(("visible_proposal_made", "visible_prompting", 1.0))
    if "repo-context-inspected" in side_effect_list and _outcome_looks_like_no_change(outcome):
        signals.append(("repo_no_change", "repo_observation", 0.9))
    if "repo-context-inspected" in side_effect_list and any(
        token in haystack
        for token in (
            "modified",
            "untracked",
            "dirty",
            "ahead",
            "behind",
            "diverged",
            "anomaly",
            "changes=",
            " m ",
            " ?? ",
        )
    ):
        signals.append(("repo_actionable_change", "loop_progression", 1.0))
    return signals


def _outcome_looks_like_no_change(outcome: dict[str, Any]) -> bool:
    summary = str(outcome.get("result_summary") or "")
    result = outcome.get("result") or outcome.get("result_json") or {}
    payload = outcome.get("payload") or outcome.get("payload_json") or {}
    haystack = " ".join(str(part) for part in (summary, result, payload)).lower()
    return any(
        token in haystack
        for token in (
            "intet nyt",
            "nothing new",
            "no change",
            "no changes",
            "no new",
            "clean working tree",
            "upstream=in-sync",
            "in-sync",
        )
    )
