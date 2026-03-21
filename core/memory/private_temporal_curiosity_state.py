from __future__ import annotations


def build_private_temporal_curiosity_state(
    *,
    private_state: dict[str, object] | None,
    private_temporal_promotion_signal: dict[str, object] | None,
    private_development_state: dict[str, object] | None,
) -> dict[str, object]:
    if not private_state or not private_temporal_promotion_signal or not private_development_state:
        return {
            "active": False,
            "current": None,
        }

    curiosity_level = str(private_state.get("curiosity") or "low").strip()[:32]
    rhythm_state = str(
        private_temporal_promotion_signal.get("rhythm_state") or "steady"
    ).strip()[:32]
    rhythm_window = str(
        private_temporal_promotion_signal.get("rhythm_window") or "watch-now"
    ).strip()
    preferred_direction = str(
        private_development_state.get("preferred_direction") or ""
    ).strip()
    confidence = str(
        private_temporal_promotion_signal.get("promotion_confidence")
        or private_development_state.get("confidence")
        or private_state.get("confidence")
        or "low"
    )[:32]
    created_at = (
        private_temporal_promotion_signal.get("created_at")
        or private_development_state.get("updated_at")
        or private_state.get("updated_at")
    )

    return {
        "active": True,
        "current": {
            "signal_id": (
                "private-temporal-curiosity-state:"
                f"{private_temporal_promotion_signal.get('signal_id') or private_state.get('state_id')}"
            ),
            "source": (
                "private-state+private-temporal-promotion-signal+"
                "private-development-state"
            ),
            "curiosity_level": curiosity_level,
            "curiosity_carry": _curiosity_carry(
                curiosity_level=curiosity_level,
                preferred_direction=preferred_direction,
                rhythm_window=rhythm_window,
            ),
            "rhythm_state": rhythm_state,
            "rhythm_carry": _rhythm_carry(rhythm_window=rhythm_window, rhythm_state=rhythm_state),
            "maturation_window": _maturation_window(
                curiosity_level=curiosity_level,
                preferred_direction=preferred_direction,
                rhythm_window=rhythm_window,
            ),
            "confidence": confidence,
            "created_at": created_at,
        },
    }


def _curiosity_carry(
    *, curiosity_level: str, preferred_direction: str, rhythm_window: str
) -> str:
    if curiosity_level == "medium" and preferred_direction.startswith("observe"):
        return "carried"
    if curiosity_level == "medium" and rhythm_window == "retain-now":
        return "held"
    if curiosity_level == "medium":
        return "active"
    return "quiet"


def _rhythm_carry(*, rhythm_window: str, rhythm_state: str) -> str:
    if rhythm_window == "retain-now":
        return "stable"
    if rhythm_window == "hold-short" or rhythm_state == "slowing":
        return "paused"
    return "watchful"


def _maturation_window(
    *, curiosity_level: str, preferred_direction: str, rhythm_window: str
) -> str:
    if curiosity_level == "medium" and preferred_direction.startswith("observe"):
        return "observe-now"
    if curiosity_level == "medium" and rhythm_window == "retain-now":
        return "carry-forward"
    return rhythm_window[:32] or "watch-now"
