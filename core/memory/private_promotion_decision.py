from __future__ import annotations


def build_private_promotion_decision_payload(
    *,
    run_id: str,
    work_id: str,
    private_temporal_promotion_signal: dict[str, str],
    private_development_state: dict[str, str],
    private_growth_note: dict[str, str],
    created_at: str,
) -> dict[str, str]:
    promotion_target = str(
        private_temporal_promotion_signal.get("promotion_target")
        or private_development_state.get("retained_pattern")
        or private_growth_note.get("helpful_signal")
        or "retain-current-pattern"
    )[:96]
    promotion_action = str(
        private_temporal_promotion_signal.get("promotion_action") or "watch"
    )[:32]
    promotion_scope = _promotion_scope(private_temporal_promotion_signal, private_growth_note)
    confidence = str(
        private_temporal_promotion_signal.get("promotion_confidence")
        or private_development_state.get("confidence")
        or private_growth_note.get("confidence")
        or "low"
    )[:32]
    return {
        "decision_id": f"private-promotion-decision:{run_id}",
        "source": (
            "private-temporal-promotion-signal:private-runtime-grounded+"
            "private-development-state"
        ),
        "run_id": run_id,
        "work_id": work_id,
        "promotion_target": promotion_target,
        "promotion_action": promotion_action,
        "promotion_scope": promotion_scope,
        "confidence": confidence,
        "created_at": created_at,
    }


def _promotion_scope(
    private_temporal_promotion_signal: dict[str, str], private_growth_note: dict[str, str]
) -> str:
    action = str(private_temporal_promotion_signal.get("promotion_action") or "").strip()
    learning_kind = str(private_growth_note.get("learning_kind") or "").strip()
    if action == "promote":
        return "private-development"
    if action == "review":
        return "private-review"
    if learning_kind == "observe":
        return "private-watch"
    return "private-hold"
