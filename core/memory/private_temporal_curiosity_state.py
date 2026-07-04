from __future__ import annotations

_LEVEL_SCALE = {"low": 0.0, "medium": 0.5, "high": 1.0}


def _observe_private_temporal_curiosity_state(*, active: bool, current: dict | None) -> None:
    """Egress-fri puls til Centralen (§24.4) — cluster=cognition. KUN aktiv-flag +
    curiosity/rhythm/confidence-labels (skalarer), ALDRIG privat tekst. record_private =
    lokal trace + tidsserie, aldrig _emit. Self-safe."""
    try:
        from core.services.central_private_observe import record_private
        cur = current or {}
        level = str(cur.get("curiosity_level") or "low")
        record_private(
            "cognition", "private_temporal_curiosity_state",
            value=_LEVEL_SCALE.get(level, 0.0) if active else 0.0,
            meta={
                "active": bool(active),
                "curiosity_level": level,
                "curiosity_carry": str(cur.get("curiosity_carry") or ""),
                "rhythm_state": str(cur.get("rhythm_state") or ""),
                "confidence": str(cur.get("confidence") or "low"),
            },
        )
    except Exception:
        pass


def build_private_temporal_curiosity_state(
    *,
    private_state: dict[str, object] | None,
    private_temporal_promotion_signal: dict[str, object] | None,
    private_development_state: dict[str, object] | None,
) -> dict[str, object]:
    if not private_state or not private_temporal_promotion_signal or not private_development_state:
        _observe_private_temporal_curiosity_state(active=False, current=None)
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

    current = {
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
    }
    _observe_private_temporal_curiosity_state(active=True, current=current)
    return {
        "active": True,
        "current": current,
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
