from __future__ import annotations

_LEVEL_SCALE = {"low": 0.0, "medium": 0.5, "high": 1.0}


def _observe_private_inner_interplay(*, active: bool, current: dict | None) -> None:
    """Egress-fri puls til Centralen (§24.4) — cluster=cognition. KUN aktiv-flag +
    mood_tone/selection_kind/confidence-labels (skalarer), ALDRIG concern/pull/pattern-
    teksten. record_private = lokal trace + tidsserie, aldrig _emit. Self-safe."""
    try:
        from core.services.central_private_observe import record_private
        cur = current or {}
        confidence = str(cur.get("state_confidence") or "low")
        record_private(
            "cognition", "private_inner_interplay",
            value=_LEVEL_SCALE.get(confidence, 0.0) if active else 0.0,
            meta={
                "active": bool(active),
                "mood_tone": str(cur.get("mood_tone") or ""),
                "selection_kind": str(cur.get("selection_kind") or ""),
                "confidence": confidence,
            },
        )
    except Exception:
        pass


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
        _observe_private_inner_interplay(active=False, current=None)
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
    current = {
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
    }
    _observe_private_inner_interplay(active=True, current=current)
    return {
        "active": True,
        "current": current,
    }
