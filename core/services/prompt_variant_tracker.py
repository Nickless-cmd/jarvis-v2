"""Prompt variant tracker — log per-variant performance for self-improvement.

Tracks which prompt fragments lead to better outcomes. Used by
auto_improvement_proposer to suggest changes based on data, not gut feel.

Concept:
- Each "variant" is a labeled string + scope (which awareness section /
  prompt fragment it applies to).
- After a turn completes, caller logs the variant used + outcome score.
- Aggregator reports: per-variant avg outcome, sample size.

Storage: state_store JSON, rolling 500 records.

Outcome score (0-100) heuristic:
- User explicit positive feedback → 90+
- Tick quality good (from agent_self_evaluation) → 70-80
- User correction/repeat → 30-50
- User dismissal → 10-30
- Default neutral → 50

Caller decides scoring; this module just stores + aggregates.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.runtime.state_store import load_json, save_json

logger = logging.getLogger(__name__)


_STATE_KEY = "prompt_variant_records"
_MAX_RECORDS = 500


def log_variant_outcome(
    *,
    scope: str,
    variant_label: str,
    outcome_score: int,
    notes: str = "",
) -> dict[str, Any]:
    """Record a variant's outcome. scope is e.g. 'awareness.tier_recommendation'."""
    if not scope or not variant_label:
        return {"status": "error", "error": "scope and variant_label required"}
    try:
        score = int(outcome_score)
        if not 0 <= score <= 100:
            return {"status": "error", "error": "outcome_score must be 0-100"}
    except (TypeError, ValueError):
        return {"status": "error", "error": "outcome_score must be an integer"}

    record = {
        "record_id": f"pvr-{uuid4().hex[:10]}",
        "logged_at": datetime.now(UTC).isoformat(),
        "scope": str(scope)[:80],
        "variant_label": str(variant_label)[:80],
        "outcome_score": score,
        "notes": str(notes)[:200],
    }
    try:
        records = load_json(_STATE_KEY, [])
        if not isinstance(records, list):
            records = []
        records.append(record)
        save_json(_STATE_KEY, records[-_MAX_RECORDS:])
    except Exception as exc:
        logger.debug("variant_tracker: persist failed: %s", exc)
        return {"status": "error", "error": str(exc)}
    return {"status": "ok", "record": record}


def variant_performance(
    *,
    scope: str | None = None,
    min_samples: int = 3,
) -> dict[str, Any]:
    """Aggregate per-variant performance, optionally filtered by scope."""
    try:
        records = load_json(_STATE_KEY, [])
        if not isinstance(records, list):
            records = []
    except Exception:
        records = []
    if scope:
        records = [r for r in records if r.get("scope") == scope]

    by_variant: dict[tuple[str, str], list[int]] = {}
    for r in records:
        key = (str(r.get("scope", "")), str(r.get("variant_label", "")))
        score = int(r.get("outcome_score") or 0)
        by_variant.setdefault(key, []).append(score)

    summaries: list[dict[str, Any]] = []
    for (sc, label), scores in by_variant.items():
        if len(scores) < min_samples:
            continue
        avg = sum(scores) / len(scores)
        summaries.append({
            "scope": sc,
            "variant_label": label,
            "n_samples": len(scores),
            "avg_score": round(avg, 1),
            "best_score": max(scores),
            "worst_score": min(scores),
        })
    summaries.sort(key=lambda s: s["avg_score"], reverse=True)
    return {
        "status": "ok",
        "variants": summaries,
        "total_records": len(records),
        "min_samples_filter": min_samples,
    }


def winning_variant(scope: str, *, min_samples: int = 5) -> dict[str, Any] | None:
    """Return the best-performing variant for a scope, or None if not enough data."""
    perf = variant_performance(scope=scope, min_samples=min_samples)
    variants = perf.get("variants") or []
    if not variants:
        return None
    return variants[0]  # already sorted desc


def _exec_log_variant_outcome(args: dict[str, Any]) -> dict[str, Any]:
    return log_variant_outcome(
        scope=str(args.get("scope") or ""),
        variant_label=str(args.get("variant_label") or ""),
        outcome_score=int(args.get("outcome_score") or 0),
        notes=str(args.get("notes") or ""),
    )


def _exec_variant_performance(args: dict[str, Any]) -> dict[str, Any]:
    return variant_performance(
        scope=args.get("scope"),
        min_samples=int(args.get("min_samples") or 3),
    )


PROMPT_VARIANT_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "log_variant_outcome",
            "description": (
                "Record a prompt-variant's outcome score (0-100). Used to "
                "track which prompt fragments produce better turns."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "scope": {"type": "string", "description": "E.g. 'awareness.tier_recommendation'."},
                    "variant_label": {"type": "string"},
                    "outcome_score": {"type": "integer"},
                    "notes": {"type": "string"},
                },
                "required": ["scope", "variant_label", "outcome_score"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "variant_performance",
            "description": "Aggregate per-variant avg score. Filter by scope. Min 3 samples by default.",
            "parameters": {
                "type": "object",
                "properties": {
                    "scope": {"type": "string"},
                    "min_samples": {"type": "integer"},
                },
                "required": [],
            },
        },
    },
]
