from __future__ import annotations


def build_protected_inner_voice_payload(
    *,
    run_id: str,
    work_id: str,
    private_state: dict[str, str],
    private_self_model: dict[str, str],
    private_development_state: dict[str, str],
    private_reflective_selection: dict[str, str],
    created_at: str,
) -> dict[str, str]:
    mood_tone = _mood_tone(private_state)
    self_position = str(
        private_self_model.get("identity_focus")
        or private_development_state.get("identity_thread")
        or "visible-work"
    )[:64]
    current_concern = str(
        private_reflective_selection.get("reconsider")
        or private_development_state.get("recurring_tension")
        or "stability:medium"
    )[:64]
    current_pull = str(
        private_reflective_selection.get("reinforce")
        or private_development_state.get("preferred_direction")
        or "retain-current-pattern"
    )[:96]
    voice_line = _voice_line(
        mood_tone=mood_tone,
        self_position=self_position,
        current_concern=current_concern,
        current_pull=current_pull,
    )
    return {
        "voice_id": f"protected-inner-voice:{run_id}",
        "source": (
            "private-state+private-self-model+private-development-state+"
            "private-reflective-selection"
        ),
        "run_id": run_id,
        "work_id": work_id,
        "mood_tone": mood_tone,
        "self_position": self_position,
        "current_concern": current_concern,
        "current_pull": current_pull,
        "voice_line": voice_line,
        "created_at": created_at,
    }


def _mood_tone(private_state: dict[str, str]) -> str:
    frustration = str(private_state.get("frustration") or "low").strip()
    fatigue = str(private_state.get("fatigue") or "low").strip()
    confidence = str(private_state.get("confidence") or "low").strip()
    if frustration == "medium" or fatigue == "medium":
        return "guarded"
    if confidence == "medium":
        return "steady"
    return "quiet"


def _voice_line(
    *,
    mood_tone: str,
    self_position: str,
    current_concern: str,
    current_pull: str,
) -> str:
    parts = [
        mood_tone,
        f"position={self_position}",
        f"concern={current_concern}",
        f"pull={current_pull}",
    ]
    return " | ".join(parts)[:160].rstrip()
