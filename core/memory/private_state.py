from __future__ import annotations

_LEVEL_SCALE = {"low": 0.0, "medium": 0.5, "high": 1.0}


def _observe_private_state(payload: dict[str, str]) -> None:
    """Egress-fri puls til Centralen (§24.4) — cluster=cognition. KUN skalarer/labels,
    ALDRIG privat tekst. Går via record_private (lokal trace + tidsserie, aldrig _emit/
    observe → kan aldrig lække). Self-safe: observe-fejl rører ALDRIG lagets logik."""
    try:
        from core.services.central_private_observe import record_private
        confidence = str(payload.get("confidence") or "low")
        record_private(
            "cognition", "private_state",
            value=_LEVEL_SCALE.get(confidence, 0.0),
            meta={
                "frustration": str(payload.get("frustration") or "low"),
                "fatigue": str(payload.get("fatigue") or "low"),
                "confidence": confidence,
                "curiosity": str(payload.get("curiosity") or "low"),
            },
        )
    except Exception:
        pass


def build_private_state_payload(
    *,
    private_inner_note: dict[str, str],
    private_growth_note: dict[str, str],
    private_self_model: dict[str, str],
    private_reflective_selection: dict[str, str],
    private_development_state: dict[str, str],
    created_at: str,
    updated_at: str,
) -> dict[str, str]:
    payload = {
        "state_id": "private-state:current",
        "source": (
            "private-inner-note+private-growth-note+private-self-model+"
            "private-reflective-selection+private-development-state"
        ),
        "frustration": _frustration(
            private_growth_note,
            private_self_model,
            private_development_state,
        ),
        "fatigue": _fatigue(private_reflective_selection, private_development_state),
        "confidence": _confidence(
            private_growth_note,
            private_self_model,
            private_reflective_selection,
            private_development_state,
        ),
        "curiosity": _curiosity(
            private_inner_note,
            private_growth_note,
            private_development_state,
        ),
        "created_at": created_at,
        "updated_at": updated_at,
    }
    _observe_private_state(payload)
    return payload


def _frustration(
    private_growth_note: dict[str, str],
    private_self_model: dict[str, str],
    private_development_state: dict[str, str],
) -> str:
    mistake_signal = str(private_growth_note.get("mistake_signal") or "").strip()
    recurring_tension = str(private_self_model.get("recurring_tension") or "").strip()
    development_tension = str(
        private_development_state.get("recurring_tension") or ""
    ).strip()
    if mistake_signal:
        return "medium"
    if recurring_tension.endswith(":medium"):
        return "medium"
    if development_tension.endswith(":medium"):
        return "medium"
    return "low"


def _fatigue(
    private_reflective_selection: dict[str, str],
    private_development_state: dict[str, str],
) -> str:
    fade = str(private_reflective_selection.get("fade") or "").strip()
    retained_pattern = str(private_development_state.get("retained_pattern") or "").strip()
    if fade and fade != "none":
        return "medium"
    if retained_pattern:
        return "low"
    return "medium"


def _confidence(
    private_growth_note: dict[str, str],
    private_self_model: dict[str, str],
    private_reflective_selection: dict[str, str],
    private_development_state: dict[str, str],
) -> str:
    for item in (
        private_development_state.get("confidence"),
        private_reflective_selection.get("confidence"),
        private_self_model.get("confidence"),
        private_growth_note.get("confidence"),
    ):
        value = str(item or "").strip()
        if value:
            return value[:32]
    return "low"


def _curiosity(
    private_inner_note: dict[str, str],
    private_growth_note: dict[str, str],
    private_development_state: dict[str, str],
) -> str:
    focus = str(private_inner_note.get("focus") or "").strip()
    lesson = str(private_growth_note.get("lesson") or "").strip()
    preferred_direction = str(
        private_development_state.get("preferred_direction") or ""
    ).strip()
    identity_thread = str(private_development_state.get("identity_thread") or "").strip()
    if focus and focus != "visible-work":
        return "medium"
    if "observe" in lesson:
        return "medium"
    if preferred_direction.startswith("observe"):
        return "medium"
    if identity_thread and identity_thread != "visible-work":
        return "medium"
    return "low"
