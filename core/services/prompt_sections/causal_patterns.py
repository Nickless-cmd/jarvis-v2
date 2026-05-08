"""Causal patterns — surface recurring (parent_kind → child_kind) flows.

Phase 3 of causal graph (per spec 2026-05-08). Where Phase 1
(causal_alerts) shows recent FAILURE chains and Phase 2
(causal_narrative) shows the SINGLE most-recent backward chain, this
section gives Jarvis a sense of TIME EXTENT — recurring causal patterns
in his own history over the last 7 days.

Goal: cross-session temporal substrate. Jarvis should notice when a
pattern is *recurring* — not just "this fired now" but "this fires
every day, you usually respond by X". This is the difference between
episodic awareness (Phase 1/2) and habituated awareness (Phase 3).

Design:
  - Aggregates causal_edges over last 7 days by (parent_kind, child_kind).
  - Filters out plumbing patterns (tool.invoked → tool.completed,
    cheap_lane_provider_failed → failover) — those are scaffolding,
    not narrative. Filters out test-data prefixes leaking from CI runs.
  - Surfaces top-N patterns with count + median/typical confidence.
  - Procedural rendering — no LLM call on prompt-assembly path.
  - TTL cache 30 min: pattern frequencies don't change minute-to-minute.
  - Returns "" silently on any error.

Awareness priority: 22 (below causal_narrative at 25 → below
causal_alerts at 30). Failures > present narrative > recurring patterns
in budget order.
"""
from __future__ import annotations

import logging
import time
from datetime import UTC, datetime, timedelta

from core.runtime.db import connect

logger = logging.getLogger(__name__)

LOOKBACK_DAYS = 7
_TOP_N = 5
_MIN_OCCURRENCES = 5  # below this it's noise, not a "pattern"

# Pure plumbing — high-frequency edges that don't tell Jarvis anything
# about his own behavior or arc. Suppressed so the section surfaces
# narrative-meaningful patterns instead.
_PLUMBING_KINDS: frozenset[str] = frozenset(
    {
        # Tool invocation lifecycle — too frequent, no narrative content
        "tool.invoked",
        "tool.completed",
        "tool.force_invoked",
        # Cheap-lane retry plumbing
        "runtime.cheap_lane_provider_completed",
        "runtime.cheap_lane_provider_failed",
        "runtime.cheap_lane_provider_failed_over",
        # Awareness-signal churn
        "runtime_awareness_signal.updated",
        "runtime_awareness_signal.created",
        "runtime_awareness_signal.stale",
        # Trace-only events
        "runtime.visible_run_execution_trace",
    }
)

# Test-data prefixes — events created during pytest runs that leaked
# into the dev DB. Suppress so production patterns aren't crowded out.
_TEST_KIND_PREFIXES: tuple[str, ...] = (
    "runtime.chain_",
    "runtime.cycle_",
    "runtime.ctx_",
    "runtime.multi_",
    "runtime.override_",
    "runtime.test_",
)

# Module-level cache — each worker maintains its own slot.
_CACHE_TTL_SECONDS = 1800.0  # 30 min
_cached_text: str | None = None
_cached_at: float = 0.0


def _is_plumbing(kind: str) -> bool:
    if kind in _PLUMBING_KINDS:
        return True
    return any(kind.startswith(p) for p in _TEST_KIND_PREFIXES)


def _fetch_patterns() -> list[dict]:
    """Return aggregated (parent_kind, child_kind) pairs over the lookback.

    Both sides plumbing → drop. Either side meaningful → keep. This is
    looser than "both meaningful" because patterns like ``tool.invoked
    → runtime.executive_action_outcome_recorded`` ARE meaningful even
    though the parent is plumbing.
    """
    cutoff = (datetime.now(UTC) - timedelta(days=LOOKBACK_DAYS)).isoformat()
    sql = (
        "SELECT pe.kind AS parent_kind, ce.kind AS child_kind, "
        "COUNT(*) AS n, AVG(edges.confidence) AS avg_conf "
        "FROM causal_edges edges "
        "JOIN events pe ON pe.id = edges.parent_event_id "
        "JOIN events ce ON ce.id = edges.child_event_id "
        "WHERE edges.created_at >= ? "
        "GROUP BY pe.kind, ce.kind "
        "HAVING n >= ? "
        "ORDER BY n DESC "
        "LIMIT 50"  # query head, then filter
    )
    with connect() as c:
        rows = c.execute(sql, (cutoff, _MIN_OCCURRENCES)).fetchall()
    out: list[dict] = []
    for r in rows:
        pk = str(r["parent_kind"])
        ck = str(r["child_kind"])
        # Both sides plumbing → not narrative
        if _is_plumbing(pk) and _is_plumbing(ck):
            continue
        out.append(
            {
                "parent_kind": pk,
                "child_kind": ck,
                "count": int(r["n"]),
                "avg_conf": float(r["avg_conf"] or 0.0),
            }
        )
    return out


def _render(patterns: list[dict]) -> str:
    if not patterns:
        return ""
    top = patterns[:_TOP_N]
    lines = ["📊 Tilbagevendende kausal-mønstre (sidste 7 dage):"]
    for p in top:
        lines.append(
            f"  · {p['parent_kind']} → {p['child_kind']} "
            f"({p['count']}× · konf {p['avg_conf']:.2f})"
        )
    return "\n".join(lines)


def causal_patterns_section() -> str:
    """Build the recurring-causal-patterns awareness section. ``""`` if none.

    Returns the cached result while within the TTL window so prompt
    assembly stays cheap. Best-effort throughout — never breaks
    prompt assembly.
    """
    global _cached_text, _cached_at
    now = time.monotonic()
    if _cached_text is not None and (now - _cached_at) < _CACHE_TTL_SECONDS:
        return _cached_text

    try:
        patterns = _fetch_patterns()
    except Exception as exc:
        logger.debug("causal_patterns: fetch failed: %s", exc)
        _cached_text = ""
        _cached_at = now
        return ""

    text = _render(patterns)
    _cached_text = text
    _cached_at = now
    return text


def invalidate_cache() -> None:
    """Force next call to rebuild. Useful in tests."""
    global _cached_text, _cached_at
    _cached_text = None
    _cached_at = 0.0
