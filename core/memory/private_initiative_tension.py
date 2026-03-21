from __future__ import annotations


def build_private_initiative_tension(
    *,
    private_state: dict[str, object] | None,
    protected_inner_voice: dict[str, object] | None,
    private_development_state: dict[str, object] | None,
    private_reflective_selection: dict[str, object] | None,
    private_temporal_promotion_signal: dict[str, object] | None,
    private_retained_memory_projection: dict[str, object] | None,
) -> dict[str, object]:
    if (
        not private_state
        or not protected_inner_voice
        or not private_development_state
        or not private_reflective_selection
        or not private_temporal_promotion_signal
    ):
        return {
            "active": False,
            "current": None,
        }

    tension_kind = _tension_kind(
        private_state=private_state,
        private_reflective_selection=private_reflective_selection,
        private_temporal_promotion_signal=private_temporal_promotion_signal,
    )
    tension_target = _tension_target(
        protected_inner_voice=protected_inner_voice,
        private_development_state=private_development_state,
        private_retained_memory_projection=private_retained_memory_projection,
    )
    tension_level = _tension_level(
        private_state=private_state,
        private_reflective_selection=private_reflective_selection,
        private_temporal_promotion_signal=private_temporal_promotion_signal,
    )
    reason = _reason(
        protected_inner_voice=protected_inner_voice,
        private_development_state=private_development_state,
        private_reflective_selection=private_reflective_selection,
        private_temporal_promotion_signal=private_temporal_promotion_signal,
    )
    confidence = str(
        private_temporal_promotion_signal.get("promotion_confidence")
        or private_state.get("confidence")
        or private_development_state.get("confidence")
        or private_reflective_selection.get("confidence")
        or "low"
    )[:32]
    created_at = (
        private_temporal_promotion_signal.get("created_at")
        or protected_inner_voice.get("created_at")
        or private_reflective_selection.get("created_at")
        or private_development_state.get("updated_at")
        or private_state.get("updated_at")
    )

    return {
        "active": True,
        "current": {
            "signal_id": (
                "private-initiative-tension:"
                f"{private_temporal_promotion_signal.get('signal_id') or private_state.get('state_id')}"
            ),
            "source": (
                "private-state+protected-inner-voice+private-development-state+"
                "private-reflective-selection+private-temporal-promotion-signal"
            ),
            "tension_kind": tension_kind,
            "tension_target": tension_target,
            "tension_level": tension_level,
            "reason": reason,
            "confidence": confidence,
            "created_at": created_at,
        },
    }


def _tension_kind(
    *,
    private_state: dict[str, object],
    private_reflective_selection: dict[str, object],
    private_temporal_promotion_signal: dict[str, object],
) -> str:
    promotion_action = str(
        private_temporal_promotion_signal.get("promotion_action") or ""
    ).strip()
    selection_kind = str(private_reflective_selection.get("selection_kind") or "").strip()
    curiosity = str(private_state.get("curiosity") or "low").strip()
    if promotion_action == "review" or selection_kind == "reconsider":
        return "unresolved"
    if curiosity == "medium":
        return "curiosity-pull"
    return "retention-pull"


def _tension_target(
    *,
    protected_inner_voice: dict[str, object],
    private_development_state: dict[str, object],
    private_retained_memory_projection: dict[str, object] | None,
) -> str:
    for item in (
        protected_inner_voice.get("current_pull"),
        private_development_state.get("retained_pattern"),
        (private_retained_memory_projection or {}).get("retained_focus"),
    ):
        value = str(item or "").strip()
        if value:
            return value[:96]
    return "retain-current-pattern"


def _tension_level(
    *,
    private_state: dict[str, object],
    private_reflective_selection: dict[str, object],
    private_temporal_promotion_signal: dict[str, object],
) -> str:
    frustration = str(private_state.get("frustration") or "low").strip()
    curiosity = str(private_state.get("curiosity") or "low").strip()
    promotion_action = str(
        private_temporal_promotion_signal.get("promotion_action") or ""
    ).strip()
    selection_kind = str(private_reflective_selection.get("selection_kind") or "").strip()
    if frustration == "medium" or promotion_action == "review":
        return "medium"
    if curiosity == "medium" or selection_kind == "retain":
        return "medium"
    return "low"


def _reason(
    *,
    protected_inner_voice: dict[str, object],
    private_development_state: dict[str, object],
    private_reflective_selection: dict[str, object],
    private_temporal_promotion_signal: dict[str, object],
) -> str:
    for item in (
        private_reflective_selection.get("reconsider"),
        protected_inner_voice.get("current_concern"),
        private_development_state.get("preferred_direction"),
        private_temporal_promotion_signal.get("rhythm_window"),
    ):
        value = str(item or "").strip()
        if value:
            return value[:64]
    return "watch-now"
