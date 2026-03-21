from __future__ import annotations


def build_private_development_state_payload(
    *,
    private_growth_note: dict[str, str],
    private_self_model: dict[str, str],
    private_reflective_selection: dict[str, str],
    created_at: str,
    updated_at: str,
) -> dict[str, str]:
    retained_pattern = _retained_pattern(
        private_growth_note=private_growth_note,
        private_reflective_selection=private_reflective_selection,
    )
    preferred_direction = str(
        private_self_model.get("growth_direction")
        or private_reflective_selection.get("selection_kind")
        or "observe"
    )[:64]
    recurring_tension = str(
        private_self_model.get("recurring_tension")
        or private_reflective_selection.get("reconsider")
        or "stability:medium"
    )[:64]
    identity_thread = str(
        private_self_model.get("identity_focus")
        or private_reflective_selection.get("identity_relevance")
        or "visible-work"
    )[:64]
    confidence = str(
        private_reflective_selection.get("confidence")
        or private_self_model.get("confidence")
        or private_growth_note.get("confidence")
        or "low"
    )[:32]
    return {
        "state_id": "private-development-state:current",
        "source": "private-growth-note+private-self-model+private-reflective-selection",
        "retained_pattern": retained_pattern,
        "preferred_direction": preferred_direction,
        "recurring_tension": recurring_tension,
        "identity_thread": identity_thread,
        "confidence": confidence,
        "created_at": created_at,
        "updated_at": updated_at,
    }


def _retained_pattern(
    *,
    private_growth_note: dict[str, str],
    private_reflective_selection: dict[str, str],
) -> str:
    reinforce = str(private_reflective_selection.get("reinforce") or "").strip()
    if reinforce:
        return reinforce[:96]
    helpful_signal = str(private_growth_note.get("helpful_signal") or "").strip()
    if helpful_signal:
        return helpful_signal[:96]
    return str(private_growth_note.get("lesson") or "retain-current-pattern")[:96]
