from __future__ import annotations


def build_private_inner_interplay(
    *,
    private_state: dict[str, object] | None,
    protected_inner_voice: dict[str, object] | None,
    private_development_state: dict[str, object] | None,
    private_reflective_selection: dict[str, object] | None,
) -> dict[str, object]:
    if (
        not private_state
        or not protected_inner_voice
        or not private_development_state
        or not private_reflective_selection
    ):
        return {
            "active": False,
            "current": None,
        }

    created_at = (
        protected_inner_voice.get("created_at")
        or private_reflective_selection.get("created_at")
        or private_development_state.get("updated_at")
        or private_state.get("updated_at")
    )
    return {
        "active": True,
        "current": {
            "interplay_id": (
                "private-inner-interplay:"
                f"{protected_inner_voice.get('voice_id') or private_state.get('state_id')}"
            ),
            "source": (
                "private-state+protected-inner-voice+private-development-state+"
                "private-reflective-selection"
            ),
            "mood_tone": protected_inner_voice.get("mood_tone"),
            "current_concern": protected_inner_voice.get("current_concern"),
            "current_pull": protected_inner_voice.get("current_pull"),
            "retained_pattern": private_development_state.get("retained_pattern"),
            "selection_kind": private_reflective_selection.get("selection_kind"),
            "state_confidence": private_state.get("confidence"),
            "created_at": created_at,
        },
    }
