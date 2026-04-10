from __future__ import annotations


def build_private_self_model_payload(
    *,
    run_id: str,
    private_inner_note: dict[str, str],
    private_growth_note: dict[str, str],
    created_at: str,
    updated_at: str,
) -> dict[str, str]:
    identity_focus = str(
        private_inner_note.get("focus")
        or private_growth_note.get("identity_signal")
        or "visible-work"
    )[:64]
    preferred_work_mode = _preferred_work_mode(private_growth_note, private_inner_note)
    recurring_tension = _recurring_tension(private_growth_note, private_inner_note)
    growth_direction = _growth_direction(private_growth_note)
    confidence = str(private_growth_note.get("confidence") or "low")[:32]
    return {
        "model_id": "private-self-model:current",
        "source": "private-growth-note+private-inner-note",
        "identity_focus": identity_focus,
        "preferred_work_mode": preferred_work_mode,
        "recurring_tension": recurring_tension,
        "growth_direction": growth_direction,
        "confidence": confidence,
        "created_at": created_at,
        "updated_at": updated_at,
    }


def _preferred_work_mode(
    private_growth_note: dict[str, str], private_inner_note: dict[str, str]
) -> str:
    focus = str(private_inner_note.get("focus") or "visible-work").strip()
    learning_kind = str(private_growth_note.get("learning_kind") or "observe").strip()
    return f"{focus}:{learning_kind}"[:64]


def _recurring_tension(
    private_growth_note: dict[str, str], private_inner_note: dict[str, str]
) -> str:
    mistake_signal = str(private_growth_note.get("mistake_signal") or "").strip()
    uncertainty = str(private_inner_note.get("uncertainty") or "medium").strip()
    if mistake_signal:
        return f"{mistake_signal}:{uncertainty}"[:64]
    # Invert uncertainty → stability: low uncertainty = high stability
    stability = {"low": "high", "medium": "medium", "high": "low"}.get(uncertainty, "medium")
    return f"stability:{stability}"[:64]


def _growth_direction(private_growth_note: dict[str, str]) -> str:
    learning_kind = str(private_growth_note.get("learning_kind") or "observe").strip()
    helpful_signal = str(private_growth_note.get("helpful_signal") or "").strip()
    if helpful_signal:
        return f"{learning_kind}:retain"[:64]
    return f"{learning_kind}:monitor"[:64]
