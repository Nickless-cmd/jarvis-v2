"""Emotional memory engine.

Captures affective state at runtime anchors (cognitive episodes, perceptual
events, MEMORY.md headings), retrieves similar past anchors via tiered
matching, and surfaces "emotional precedent" cues to the cognitive
conductor.

See docs/superpowers/specs/2026-05-04-emotional-memory-engine-design.md
for the full design.
"""
from __future__ import annotations

import json
import logging
import random
from datetime import UTC, datetime

from core.eventbus.bus import event_bus
from core.runtime.db import insert_emotional_memory_anchor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Outcome auto-derivation
# ---------------------------------------------------------------------------


def _classify_error(error: str) -> str:
    """Map raw error text to a coarse category for retrieval matching."""
    text = (error or "").lower()
    if not text.strip():
        return "none"
    if "timeout" in text or "timed out" in text:
        return "timeout"
    if "bad request" in text or "http 400" in text:
        return "bad_request"
    if "tool" in text and ("error" in text or "fail" in text):
        return "tool_error"
    return "other"


def _count_tool_errors(error: str, tool_names: list[str]) -> int:
    """Heuristically count how many tools in a run failed.

    Looks for occurrences of "tool <name> ... fail|error" patterns. This is
    intentionally rough — the goal is a 0/1/many bucket for outcome scoring.
    """
    text = (error or "").lower()
    if not text.strip():
        return 0
    count = 0
    for name in tool_names or []:
        nm = str(name or "").lower().strip()
        if not nm:
            continue
        if nm in text and ("error" in text or "fail" in text):
            count += 1
    if count == 0:
        if "fail" in text or "error" in text:
            return 1
    return count


def _derive_outcome_score(
    *, status: str, error: str, tool_error_count: int
) -> tuple[float | None, str | None]:
    """Auto-deriv outcome score from structured episode fields.

    Returns (score, source) where score is in [-1, 1] and source is "auto"
    or None when no determination can be made.
    """
    s = (status or "").strip().lower()
    err = (error or "").lower()
    has_error = bool(err.strip())
    has_strong_error = "timeout" in err or "bad request" in err or "http 400" in err

    if s == "completed" and not has_error and tool_error_count == 0:
        return (0.6, "auto")
    if s == "completed" and (has_error or tool_error_count > 0):
        return (0.0, "auto")
    if s == "interrupted":
        return (-0.4, "auto")
    if has_strong_error or s == "error":
        return (-0.7, "auto")
    if s == "cancelled":
        return (-0.1, "auto")
    return (None, None)


# ---------------------------------------------------------------------------
# Capture flow
# ---------------------------------------------------------------------------


def _read_current_mood() -> tuple[str, float]:
    """Return (mood, intensity). Raises if oscillator is unavailable."""
    from core.services.mood_oscillator import get_current_mood, get_mood_intensity
    return (str(get_current_mood() or ""), float(get_mood_intensity()))


def _read_current_dimensions() -> dict[str, float | None]:
    """Return the 5-dimension live emotional state. May raise — caller handles."""
    from core.services.affective_meta_state import build_affective_meta_state_surface
    surface = build_affective_meta_state_surface()
    live = (surface or {}).get("live_emotional_state") or {}
    return {
        "confidence": _coerce_float_or_none(live.get("confidence")),
        "curiosity": _coerce_float_or_none(live.get("curiosity")),
        "frustration": _coerce_float_or_none(live.get("frustration")),
        "fatigue": _coerce_float_or_none(live.get("fatigue")),
        "trust": _coerce_float_or_none(live.get("trust")),
    }


def _coerce_float_or_none(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def capture_emotional_anchor(
    *,
    anchor_type: str,
    anchor_id: str,
    context_features: dict[str, object],
    auto_outcome_inputs: dict[str, object] | None = None,
    source: str = "",
    notes: str | None = None,
) -> dict[str, object] | None:
    """Snapshot affect for an anchor and persist it.

    Returns the persisted summary dict, or None on failure (never raises).
    """
    try:
        try:
            mood, intensity = _read_current_mood()
        except Exception as exc:
            logger.debug("emotional_memory: mood read failed: %s", exc)
            return None

        try:
            dims = _read_current_dimensions()
        except Exception as exc:
            logger.debug("emotional_memory: dimension read failed: %s", exc)
            dims = {}

        outcome_score: float | None = None
        outcome_source: str | None = None
        if auto_outcome_inputs:
            try:
                outcome_score, outcome_source = _derive_outcome_score(
                    status=str(auto_outcome_inputs.get("outcome_status") or ""),
                    error=str(auto_outcome_inputs.get("error") or ""),
                    tool_error_count=int(auto_outcome_inputs.get("tool_error_count") or 0),
                )
            except Exception:
                outcome_score, outcome_source = (None, None)

        captured_at = datetime.now(UTC).isoformat()
        try:
            insert_emotional_memory_anchor(
                anchor_type=str(anchor_type),
                anchor_id=str(anchor_id),
                captured_at=captured_at,
                mood=str(mood)[:60],
                intensity=float(intensity),
                confidence=dims.get("confidence"),
                curiosity=dims.get("curiosity"),
                frustration=dims.get("frustration"),
                fatigue=dims.get("fatigue"),
                trust=dims.get("trust"),
                outcome_score=outcome_score,
                outcome_source=outcome_source,
                context_features_json=json.dumps(context_features or {}, ensure_ascii=False)[:4000],
                source=source or None,
                notes=notes,
            )
        except Exception as exc:
            logger.warning("emotional_memory: persist failed: %s", exc)
            return None

        try:
            event_bus.publish(
                "emotional_memory.anchor_captured",
                {
                    "anchor_type": anchor_type,
                    "anchor_id": anchor_id,
                    "mood": mood,
                    "intensity": intensity,
                    "outcome_score": outcome_score,
                },
            )
        except Exception:
            pass

        try:
            if random.random() < 0.01:
                prune_aged_anchors()
        except Exception:
            pass

        return {
            "anchor_type": anchor_type,
            "anchor_id": anchor_id,
            "captured_at": captured_at,
            "mood": mood,
            "intensity": intensity,
            "outcome_score": outcome_score,
            "outcome_source": outcome_source,
        }
    except Exception as exc:
        logger.warning("emotional_memory: capture top-level failure: %s", exc)
        return None


def prune_aged_anchors() -> int:
    """Stub — fully implemented in Task 5. Returning 0 lets capture's
    probabilistic prune call be a no-op until the real implementation lands."""
    return 0
