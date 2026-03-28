from __future__ import annotations


def build_private_temporal_promotion_signal_payload(
    *,
    run_id: str,
    work_id: str,
    private_state: dict[str, str],
    private_reflective_selection: dict[str, str],
    private_development_state: dict[str, str],
    protected_inner_voice: dict[str, str],
    created_at: str,
) -> dict[str, str]:
    rhythm_state = _rhythm_state(private_state, protected_inner_voice)
    rhythm_window = _rhythm_window(private_state)
    promotion_target = str(
        private_development_state.get("retained_pattern")
        or private_reflective_selection.get("reinforce")
        or protected_inner_voice.get("current_pull")
        or "retain-current-pattern"
    )[:96]
    promotion_action = _promotion_action(private_reflective_selection, private_state)
    promotion_confidence = str(
        private_state.get("confidence")
        or private_reflective_selection.get("confidence")
        or private_development_state.get("confidence")
        or "low"
    )[:32]
    return {
        "signal_id": f"private-temporal-promotion-signal:{run_id}",
        "source": (
            "private-state+private-reflective-selection+private-development-state:"
            "private-runtime-grounded+"
            "protected-inner-voice"
        ),
        "run_id": run_id,
        "work_id": work_id,
        "rhythm_state": rhythm_state,
        "rhythm_window": rhythm_window,
        "promotion_target": promotion_target,
        "promotion_action": promotion_action,
        "promotion_confidence": promotion_confidence,
        "created_at": created_at,
    }


def _rhythm_state(
    private_state: dict[str, str], protected_inner_voice: dict[str, str]
) -> str:
    mood_tone = str(protected_inner_voice.get("mood_tone") or "").strip()
    fatigue = str(private_state.get("fatigue") or "low").strip()
    frustration = str(private_state.get("frustration") or "low").strip()
    if fatigue == "medium":
        return "slowing"
    if frustration == "medium" or mood_tone == "guarded":
        return "guarded"
    return "steady"


def _rhythm_window(private_state: dict[str, str]) -> str:
    fatigue = str(private_state.get("fatigue") or "low").strip()
    confidence = str(private_state.get("confidence") or "low").strip()
    if fatigue == "medium":
        return "hold-short"
    if confidence == "medium":
        return "retain-now"
    return "watch-now"


def _promotion_action(
    private_reflective_selection: dict[str, str], private_state: dict[str, str]
) -> str:
    selection_kind = str(
        private_reflective_selection.get("selection_kind") or "observe"
    ).strip()
    fatigue = str(private_state.get("fatigue") or "low").strip()
    if fatigue == "medium":
        return "hold"
    if selection_kind == "retain":
        return "promote"
    if selection_kind == "reconsider":
        return "review"
    return "watch"
