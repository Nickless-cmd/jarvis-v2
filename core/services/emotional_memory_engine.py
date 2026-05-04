"""Emotional memory engine.

Captures affective state at runtime anchors (cognitive episodes, perceptual
events, MEMORY.md headings), retrieves similar past anchors via tiered
matching, and surfaces "emotional precedent" cues to the cognitive
conductor.

See docs/superpowers/specs/2026-05-04-emotional-memory-engine-design.md
for the full design.
"""
from __future__ import annotations

import logging

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
