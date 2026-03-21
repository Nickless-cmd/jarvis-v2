from __future__ import annotations


def build_private_retained_memory_record_payload(
    *,
    run_id: str,
    work_id: str,
    private_promotion_decision: dict[str, str],
    private_development_state: dict[str, str],
    private_growth_note: dict[str, str],
    private_self_model: dict[str, str],
    created_at: str,
) -> dict[str, str]:
    retained_value = str(
        private_promotion_decision.get("promotion_target")
        or private_development_state.get("retained_pattern")
        or private_growth_note.get("helpful_signal")
        or "retain-current-pattern"
    )[:96]
    retained_kind = _retained_kind(private_promotion_decision, private_growth_note)
    retention_scope = str(
        private_promotion_decision.get("promotion_scope")
        or private_self_model.get("identity_focus")
        or "private-development"
    )[:64]
    retention_horizon = _retention_horizon(
        retention_scope=retention_scope,
        private_development_state=private_development_state,
        private_self_model=private_self_model,
    )
    confidence = str(
        private_promotion_decision.get("confidence")
        or private_development_state.get("confidence")
        or private_growth_note.get("confidence")
        or "low"
    )[:32]
    return {
        "record_id": f"private-retained-memory-record:{run_id}",
        "source": "private-promotion-decision+private-development-state",
        "run_id": run_id,
        "work_id": work_id,
        "retained_value": retained_value,
        "retained_kind": retained_kind,
        "retention_scope": retention_scope,
        "retention_horizon": retention_horizon,
        "confidence": confidence,
        "created_at": created_at,
    }


def _retained_kind(
    private_promotion_decision: dict[str, str], private_growth_note: dict[str, str]
) -> str:
    action = str(private_promotion_decision.get("promotion_action") or "").strip()
    learning_kind = str(private_growth_note.get("learning_kind") or "").strip()
    if action == "promote":
        return "reinforced-pattern"
    if action == "review":
        return "reconsidered-pattern"
    if learning_kind == "observe":
        return "observed-pattern"
    return "held-pattern"


def _retention_horizon(
    *,
    retention_scope: str,
    private_development_state: dict[str, str],
    private_self_model: dict[str, str],
) -> str:
    preferred_direction = str(
        private_development_state.get("preferred_direction") or ""
    ).strip()
    identity_thread = str(private_development_state.get("identity_thread") or "").strip()
    growth_direction = str(private_self_model.get("growth_direction") or "").strip()
    if (
        retention_scope == "private-development"
        or identity_thread == "visible-work"
        or preferred_direction.endswith("retain")
        or growth_direction.endswith(":retain")
    ):
        return "development-stable"
    return "short-term"
