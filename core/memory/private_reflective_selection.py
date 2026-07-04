from __future__ import annotations

_LEVEL_SCALE = {"low": 0.0, "medium": 0.5, "high": 1.0}


def _observe_private_reflective_selection(payload: dict[str, str]) -> None:
    """Egress-fri puls til Centralen (§24.4) — cluster=cognition. KUN selection_kind/
    confidence-labels (skalarer), ALDRIG reinforce/reconsider-teksten. record_private =
    lokal trace + tidsserie, aldrig _emit. Self-safe."""
    try:
        from core.services.central_private_observe import record_private
        confidence = str(payload.get("confidence") or "low")
        record_private(
            "cognition", "private_reflective_selection",
            value=_LEVEL_SCALE.get(confidence, 0.0),
            meta={
                "selection_kind": str(payload.get("selection_kind") or "observe"),
                "confidence": confidence,
                "fades": str(payload.get("fade") or "none") != "none",
            },
        )
    except Exception:
        pass


def build_private_reflective_selection_payload(
    *,
    run_id: str,
    work_id: str,
    private_growth_note: dict[str, str],
    private_self_model: dict[str, str],
    created_at: str,
) -> dict[str, str]:
    selection_kind = _selection_kind(private_growth_note)
    reinforce = _reinforce(private_growth_note)
    reconsider = _reconsider(private_growth_note, private_self_model)
    fade = _fade(private_growth_note)
    identity_relevance = str(
        private_self_model.get("identity_focus")
        or private_growth_note.get("identity_signal")
        or "visible-work"
    )[:64]
    confidence = str(
        private_self_model.get("confidence")
        or private_growth_note.get("confidence")
        or "low"
    )[:32]
    payload = {
        "signal_id": f"private-reflective-selection:{run_id}",
        "source": "private-growth-note:private-runtime-grounded+private-self-model",
        "run_id": run_id,
        "work_id": work_id,
        "selection_kind": selection_kind,
        "reinforce": reinforce,
        "reconsider": reconsider,
        "fade": fade,
        "identity_relevance": identity_relevance,
        "confidence": confidence,
        "created_at": created_at,
    }
    _observe_private_reflective_selection(payload)
    return payload


def _selection_kind(private_growth_note: dict[str, str]) -> str:
    learning_kind = str(private_growth_note.get("learning_kind") or "observe").strip()
    if learning_kind == "reinforce":
        return "retain"
    if learning_kind == "adjust":
        return "reconsider"
    return "observe"


def _reinforce(private_growth_note: dict[str, str]) -> str:
    helpful_signal = str(private_growth_note.get("helpful_signal") or "").strip()
    if helpful_signal:
        return helpful_signal[:96]
    return str(private_growth_note.get("lesson") or "retain-current-signal")[:96]


def _reconsider(
    private_growth_note: dict[str, str], private_self_model: dict[str, str]
) -> str:
    mistake_signal = str(private_growth_note.get("mistake_signal") or "").strip()
    recurring_tension = str(private_self_model.get("recurring_tension") or "").strip()
    if mistake_signal:
        return mistake_signal[:64]
    return recurring_tension[:64]


def _fade(private_growth_note: dict[str, str]) -> str:
    learning_kind = str(private_growth_note.get("learning_kind") or "").strip().lower()
    if learning_kind == "observe":
        return "low-signal-observation"
    return "none"
