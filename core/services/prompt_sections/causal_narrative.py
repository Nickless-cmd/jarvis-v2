"""Causal narrative — surface "how you landed here" in the prompt.

Phase 2 of causal graph (per spec 2026-05-08). Where ``causal_alerts``
shows recent FAILURE chains, this section shows the most recent
narrative-worthy anchor event and what led up to it — independent of
whether anything went wrong.

Goal: give Jarvis a permanent felt continuity ("the last thing that
moved me was X, after Y and Z") instead of starting every turn from
nothing. Not for debugging — for self-coherence.

Design:
  - Anchor selection prefers narrative-meaningful kinds (decisions,
    identity events, executive outcomes, memory consolidation, visible
    run starts) over plumbing chatter (cheap_lane_provider_completed,
    runtime_awareness_signal.updated).
  - Walks BACKWARD from the anchor through causal_edges to render
    "what brought us here". Forward-walk would tell "what happened
    next" — but the anchor IS "now-ish", so backward is the relevant
    direction for a self-coherence narrative.
  - Procedural rendering — no LLM call on the prompt-assembly critical
    path. Phase 2.5 (later) may add an LLM-summarised variant cached
    by a background daemon.
  - TTL cache 5 min so prompt-assembly stays fast even with this
    section enabled. Story doesn't need second-resolution freshness.
  - Returns "" silently on any error (best-effort awareness item).

Awareness priority: 25 (slightly below causal_alerts at 30). Failures
should always outrank ambient narrative; if budget is tight, narrative
drops first.
"""
from __future__ import annotations

import logging
import time
from datetime import UTC, datetime, timedelta

from core.runtime.db import connect

logger = logging.getLogger(__name__)

# How far back to look for an anchor. Longer = more chance of catching
# a quiet stretch's narrative; shorter = freshness. 90 min keeps us
# within the same conversational arc without dredging up yesterday.
LOOKBACK_MINUTES = 90

# Anchor kinds in priority order. First match wins (most recent
# instance of highest-priority kind found in window).
_ANCHOR_KINDS = (
    # Identity-shaping events — rare, always narrative-relevant
    "identity.drift_detected",
    "identity.mutation_applied",
    # Outcomes from the executive loop
    "runtime.executive_action_outcome_recorded",
    "behavioral_decision_review.completed",
    # Memory consolidation — "what stuck"
    "memory.end_of_run_consolidation",
    "cognitive_experiential.memory_created",
    # Lifecycle anchors — most common fallback
    "runtime.visible_run_started",
    "runtime.agentic_round_start",
)

# Walk this far back through causal_edges from the anchor.
_CHAIN_DEPTH = 4

# Edge confidence cutoff. Inference daemon mints a lot of low-confidence
# temporal edges; for narrative we want the spine, not the speculation.
_MIN_CONFIDENCE = 0.7

# Per-call cache. Module-level so each worker maintains its own slot.
# Story doesn't change second-by-second; 5 min is plenty.
_CACHE_TTL_SECONDS = 300.0
_cached_text: str | None = None
_cached_at: float = 0.0


def _fetch_recent_anchor() -> dict | None:
    """Return the most narrative-worthy event in the lookback window.

    Walks ``_ANCHOR_KINDS`` in priority order; returns the most recent
    event of the highest-priority kind that has at least one entry in
    the window. Returns ``None`` if nothing matches.
    """
    cutoff = (datetime.now(UTC) - timedelta(minutes=LOOKBACK_MINUTES)).isoformat()
    with connect() as c:
        for kind in _ANCHOR_KINDS:
            row = c.execute(
                "SELECT id, kind, created_at FROM events "
                "WHERE kind = ? AND created_at >= ? "
                "ORDER BY id DESC LIMIT 1",
                (kind, cutoff),
            ).fetchone()
            if row is not None:
                return {
                    "id": int(row["id"]),
                    "kind": str(row["kind"]),
                    "created_at": str(row["created_at"]),
                }
    return None


def _format_chain(anchor: dict) -> str:
    """Render the backward chain from anchor as a compact narrative.

    Output shape (multi-line):
      🌊 Sådan landede du her (sidste 90 min):
        nu: anchor.kind (HH:MM)
          ← parent.kind (HH:MM)
          ← grandparent.kind (HH:MM)
    """
    from core.services.causal_graph import query_causal_chain

    chain = query_causal_chain(
        event_id=int(anchor["id"]),
        direction="backward",
        max_depth=_CHAIN_DEPTH,
        min_confidence=_MIN_CONFIDENCE,
    )

    anchor_ts = anchor["created_at"][11:16] if len(anchor["created_at"]) >= 16 else anchor["created_at"]
    lines = ["🌊 Sådan landede du her (sidste 90 min):"]
    lines.append(f"  nu: {anchor['kind']} ({anchor_ts})")
    if not chain["chain"]:
        lines.append("    ← <ingen high-confidence kausal-historik bag dette>")
        return "\n".join(lines)
    for step in chain["chain"]:
        ev = step["event"]
        ts = ev["created_at"][11:16] if len(ev.get("created_at", "")) >= 16 else ""
        lines.append(f"    ← {ev['kind']} ({ts})")
    return "\n".join(lines)


def causal_narrative_section() -> str:
    """Build the causal-narrative awareness section. Returns "" if no anchor.

    Caches result for ``_CACHE_TTL_SECONDS`` so prompt-assembly stays
    cheap. Best-effort throughout — never breaks prompt assembly.
    """
    global _cached_text, _cached_at
    now = time.monotonic()
    if _cached_text is not None and (now - _cached_at) < _CACHE_TTL_SECONDS:
        return _cached_text

    try:
        anchor = _fetch_recent_anchor()
    except Exception as exc:
        logger.debug("causal_narrative: anchor fetch failed: %s", exc)
        _cached_text = ""
        _cached_at = now
        return ""

    if anchor is None:
        _cached_text = ""
        _cached_at = now
        return ""

    try:
        text = _format_chain(anchor)
    except Exception as exc:
        logger.debug("causal_narrative: chain render failed: %s", exc)
        text = ""

    _cached_text = text
    _cached_at = now
    return text


def invalidate_cache() -> None:
    """Force next call to rebuild. Useful in tests."""
    global _cached_text, _cached_at
    _cached_text = None
    _cached_at = 0.0
