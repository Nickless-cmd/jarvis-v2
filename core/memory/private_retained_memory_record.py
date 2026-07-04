from __future__ import annotations

_LEVEL_SCALE = {"low": 0.0, "medium": 0.5, "high": 1.0}


def _observe_private_retained_memory_record(payload: dict[str, str]) -> None:
    """Egress-fri puls til Centralen (§24.4) — cluster=cognition. KUN kind/scope/horizon/
    confidence-labels (skalarer), ALDRIG retained_value-teksten (det faktiske huskede indhold).
    record_private = lokal trace + tidsserie, aldrig _emit. Self-safe."""
    try:
        from core.services.central_private_observe import record_private
        confidence = str(payload.get("confidence") or "low")
        record_private(
            "cognition", "private_retained_memory_record",
            value=_LEVEL_SCALE.get(confidence, 0.0),
            meta={
                "retained_kind": str(payload.get("retained_kind") or ""),
                "retention_scope": str(payload.get("retention_scope") or ""),
                "retention_horizon": str(payload.get("retention_horizon") or "transient"),
                "confidence": confidence,
            },
        )
    except Exception:
        pass


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
    )[:200]
    retained_kind = _retained_kind(private_promotion_decision, private_growth_note)
    retention_scope = _humanize_scope(str(
        private_promotion_decision.get("promotion_scope")
        or private_self_model.get("identity_focus")
        or "general"
    )[:64])
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
    payload = {
        "record_id": f"private-retained-memory-record:{run_id}",
        "source": (
            "private-promotion-decision:private-runtime-grounded+"
            "private-development-state"
        ),
        "run_id": run_id,
        "work_id": work_id,
        "retained_value": retained_value,
        "retained_kind": retained_kind,
        "retention_scope": retention_scope,
        "retention_horizon": retention_horizon,
        "confidence": confidence,
        "created_at": created_at,
    }
    _observe_private_retained_memory_record(payload)
    return payload


def _retained_kind(
    private_promotion_decision: dict[str, str], private_growth_note: dict[str, str]
) -> str:
    action = str(private_promotion_decision.get("promotion_action") or "").strip()
    learning_kind = str(private_growth_note.get("learning_kind") or "").strip()
    if action == "promote":
        return "reinforced pattern"
    if action == "review":
        return "reconsidered pattern"
    if learning_kind == "observe":
        return "observed pattern"
    return "held pattern"


def _humanize_scope(scope: str) -> str:
    scope_map = {
        "private-development": "development",
        "private-review": "review",
        "private-watch": "observation",
        "private-hold": "short-term",
        "visible-work": "conversation",
    }
    return scope_map.get(scope, scope)


def _retention_horizon(
    *,
    retention_scope: str,
    private_development_state: dict[str, str],
    private_self_model: dict[str, str],
) -> str:
    preferred_direction = str(
        private_development_state.get("preferred_direction") or ""
    ).strip()
    growth_direction = str(private_self_model.get("growth_direction") or "").strip()
    if (
        retention_scope in {"development", "private-development"}
        or preferred_direction.endswith("retain")
        or growth_direction.endswith(":retain")
    ):
        return "persistent"
    return "transient"
