"""Taste Profile — accumulating aesthetic preferences for code, design, and communication.

Grows over time from corrections (user fixes Jarvis) and positive signals.
Injected into visible prompt via cognitive_state_assembly.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import UTC, datetime

from core.eventbus.bus import event_bus
from core.runtime.db import (
    get_latest_cognitive_taste_profile,
    upsert_cognitive_taste_profile,
)

logger = logging.getLogger(__name__)

# Default taste dimensions
_DEFAULT_CODE_TASTE = {
    "prefers_inline_styles": 0.5,
    "prefers_small_functions": 0.5,
    "prefers_explicit_over_implicit": 0.5,
    "dislikes_deep_nesting": 0.5,
    "prefers_danish_comments": 0.5,
}

_DEFAULT_DESIGN_TASTE = {
    "compact_over_spacious": 0.5,
    "data_dense": 0.5,
    "dark_theme": 0.5,
    "mono_fonts_for_data": 0.5,
}

_DEFAULT_COMMUNICATION_TASTE = {
    "show_code_not_talk": 0.5,
    "danish_responses": 0.5,
    "avoid_bullet_lists": 0.5,
    "humor_appropriate": 0.5,
    "concise_over_verbose": 0.5,
}

# Keyword signals for taste detection
_CORRECTION_SIGNALS = {
    "kort": ("communication_taste", "concise_over_verbose", 0.03),
    "kortere": ("communication_taste", "concise_over_verbose", 0.05),
    "dansk": ("communication_taste", "danish_responses", 0.05),
    "kompakt": ("design_taste", "compact_over_spacious", 0.03),
    "inline": ("code_taste", "prefers_inline_styles", 0.03),
    "mørk": ("design_taste", "dark_theme", 0.03),
    "mono": ("design_taste", "mono_fonts_for_data", 0.03),
    "kode": ("communication_taste", "show_code_not_talk", 0.03),
}

_POSITIVE_SIGNALS = {
    "godt": 0.01,
    "perfekt": 0.02,
    "ja": 0.005,
    "præcis": 0.02,
    "fedt": 0.01,
}


def update_taste_from_run(
    *,
    run_id: str,
    user_message: str,
    was_corrected: bool,
    outcome_status: str,
) -> dict[str, object] | None:
    """Update taste profile based on a visible run interaction."""
    current = get_latest_cognitive_taste_profile()
    code_taste = _safe_json(current.get("code_taste") if current else None, _DEFAULT_CODE_TASTE)
    design_taste = _safe_json(current.get("design_taste") if current else None, _DEFAULT_DESIGN_TASTE)
    comm_taste = _safe_json(current.get("communication_taste") if current else None, _DEFAULT_COMMUNICATION_TASTE)
    evidence_count = int(current.get("evidence_count", 0)) if current else 0

    msg_lower = user_message.lower()
    changed = False

    # Correction signals — user is correcting Jarvis
    if was_corrected:
        for keyword, (category, dimension, delta) in _CORRECTION_SIGNALS.items():
            if keyword in msg_lower:
                target = {"code_taste": code_taste, "design_taste": design_taste, "communication_taste": comm_taste}[category]
                old = float(target.get(dimension, 0.5))
                target[dimension] = min(1.0, old + delta)
                changed = True
                evidence_count += 1

    # Positive signals — user is happy
    if outcome_status in ("completed", "success"):
        for keyword, delta in _POSITIVE_SIGNALS.items():
            if keyword in msg_lower:
                # Reinforce current taste (small nudge toward extremes)
                for taste_dict in (code_taste, design_taste, comm_taste):
                    for dim, val in taste_dict.items():
                        if val > 0.6:
                            taste_dict[dim] = min(1.0, val + delta * 0.5)
                        elif val < 0.4:
                            taste_dict[dim] = max(0.0, val - delta * 0.5)
                changed = True
                evidence_count += 1

    if not changed:
        return None

    result = upsert_cognitive_taste_profile(
        code_taste=json.dumps(code_taste, ensure_ascii=False),
        design_taste=json.dumps(design_taste, ensure_ascii=False),
        communication_taste=json.dumps(comm_taste, ensure_ascii=False),
        evidence_count=evidence_count,
    )

    event_bus.publish(
        "cognitive_taste.profile_updated",
        {"run_id": run_id, "evidence_count": evidence_count},
    )
    return result


def update_taste_async(
    *,
    run_id: str,
    user_message: str,
    was_corrected: bool,
    outcome_status: str,
) -> None:
    threading.Thread(
        target=lambda: _safe(update_taste_from_run,
                             run_id=run_id, user_message=user_message,
                             was_corrected=was_corrected, outcome_status=outcome_status),
        daemon=True,
    ).start()


def get_crystallized_tastes() -> dict[str, float]:
    """Return taste dimensions that have moved decisively (>0.72 or <0.28)."""
    current = get_latest_cognitive_taste_profile()
    if not current:
        return {}
    result: dict[str, float] = {}
    for field in ("code_taste", "design_taste", "communication_taste"):
        dims = _safe_json(current.get(field), {})
        for dim, val in dims.items():
            v = float(val)
            if v > 0.72 or v < 0.28:
                result[dim] = round(v, 2)
    return result


def build_taste_profile_surface() -> dict[str, object]:
    current = get_latest_cognitive_taste_profile()
    return {
        "active": current is not None,
        "current": current,
        "summary": (
            f"v{current['version']}, {current.get('evidence_count', 0)} evidence points"
            if current else "No taste profile yet"
        ),
    }


def _safe(fn, **kwargs):
    try:
        fn(**kwargs)
    except Exception:
        logger.debug("taste_profile: async failed", exc_info=True)


def _safe_json(value, default):
    if isinstance(value, dict):
        return {**default, **value}
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return {**default, **parsed}
        except Exception:
            pass
    return dict(default)
