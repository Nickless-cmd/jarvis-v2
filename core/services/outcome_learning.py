"""Outcome Learning — record observations, let old evidence decay.

Concept from jarvis-ai (2026-03), inspired by Jarvis' own audit: track
context→outcome observations with a weight that decays over time, so old
evidence matters less but is not forgotten abruptly.

Use cases:
- "This prompt pattern succeeded" → record_outcome(context="prompt:X", outcome="success")
- "This tool failed here" → record_outcome(context="tool:Y", outcome="error")
- Query pattern_strength(context) to see decayed total evidence

Decay: exponential with 30-day half-life. Evidence from yesterday is
near-full-weight; evidence from last month is at half; from 3 months is
~1/8. Never zero — slow fade.
"""
from __future__ import annotations

import json
import logging
import math
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_STORAGE_REL = "workspaces/default/runtime/outcome_learning.json"
_HALF_LIFE_DAYS = 30.0
_DECAY_COEF = math.log(2) / _HALF_LIFE_DAYS  # per day
_MAX_RECORDS = 5000  # keep most recent — older drop from storage


def _storage_path() -> Path:
    base = os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2")
    return Path(base) / _STORAGE_REL


def _load() -> list[dict[str, Any]]:
    path = _storage_path()
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except Exception as exc:
        logger.warning("outcome_learning: load failed: %s", exc)
    return []


def _save(items: list[dict[str, Any]]) -> None:
    path = _storage_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        tmp.replace(path)
    except Exception as exc:
        logger.warning("outcome_learning: save failed: %s", exc)


def record_outcome(
    *,
    context: str,
    outcome: str,
    weight: float = 1.0,
    metadata: dict[str, Any] | None = None,
) -> str:
    """Record a single observation. outcome is free-form ('success', 'error',
    'refused', 'preferred', etc.). weight lets you up/downweight strong signals.
    """
    items = _load()
    rid = f"oc-{uuid4().hex[:12]}"
    items.append({
        "record_id": rid,
        "context": str(context)[:200],
        "outcome": str(outcome)[:80],
        "weight": float(weight),
        "metadata": dict(metadata or {}),
        "recorded_at": datetime.now(UTC).isoformat(),
    })
    if len(items) > _MAX_RECORDS:
        items = items[-_MAX_RECORDS:]
    _save(items)
    return rid


def _decay_factor(recorded_at: str, now: datetime) -> float:
    try:
        dt = datetime.fromisoformat(str(recorded_at).replace("Z", "+00:00"))
    except Exception:
        return 0.0
    days = max(0.0, (now - dt).total_seconds() / 86400)
    return math.exp(-_DECAY_COEF * days)


def pattern_strength(context: str, *, outcome: str | None = None) -> dict[str, Any]:
    """Return decayed totals for a given context, optionally per-outcome."""
    items = _load()
    now = datetime.now(UTC)
    matching = [i for i in items if i.get("context") == context]
    if outcome is not None:
        matching = [i for i in matching if i.get("outcome") == outcome]
    total = 0.0
    by_outcome: dict[str, float] = {}
    newest: datetime | None = None
    for i in matching:
        factor = _decay_factor(str(i.get("recorded_at")), now)
        weight = float(i.get("weight") or 1.0) * factor
        total += weight
        key = str(i.get("outcome") or "")
        by_outcome[key] = by_outcome.get(key, 0.0) + weight
        try:
            dt = datetime.fromisoformat(str(i.get("recorded_at")).replace("Z", "+00:00"))
            if newest is None or dt > newest:
                newest = dt
        except Exception:
            pass
    return {
        "context": context,
        "outcome": outcome,
        "strength": round(total, 3),
        "by_outcome": {k: round(v, 3) for k, v in by_outcome.items()},
        "raw_count": len(matching),
        "newest_observation_at": newest.isoformat() if newest else None,
    }


def top_patterns(*, limit: int = 10, outcome: str | None = None) -> list[dict[str, Any]]:
    """Return the N strongest patterns (highest decayed strength)."""
    items = _load()
    now = datetime.now(UTC)
    by_context: dict[str, float] = {}
    context_outcomes: dict[str, dict[str, float]] = {}
    for i in items:
        if outcome is not None and i.get("outcome") != outcome:
            continue
        ctx = str(i.get("context") or "")
        factor = _decay_factor(str(i.get("recorded_at")), now)
        w = float(i.get("weight") or 1.0) * factor
        by_context[ctx] = by_context.get(ctx, 0.0) + w
        bucket = context_outcomes.setdefault(ctx, {})
        oc = str(i.get("outcome") or "")
        bucket[oc] = bucket.get(oc, 0.0) + w
    ranked = sorted(by_context.items(), key=lambda kv: kv[1], reverse=True)
    return [
        {
            "context": ctx,
            "strength": round(strength, 3),
            "by_outcome": {k: round(v, 3) for k, v in context_outcomes.get(ctx, {}).items()},
        }
        for ctx, strength in ranked[:limit]
    ]


def prune_old_records(*, min_weight: float = 0.01) -> int:
    """Drop records whose decayed weight is below min_weight. Returns count dropped."""
    items = _load()
    now = datetime.now(UTC)
    kept = []
    dropped = 0
    for i in items:
        factor = _decay_factor(str(i.get("recorded_at")), now)
        effective = float(i.get("weight") or 1.0) * factor
        if effective < min_weight:
            dropped += 1
            continue
        kept.append(i)
    if dropped > 0:
        _save(kept)
    return dropped


def tick(_seconds: float = 0.0) -> dict[str, Any]:
    """Heartbeat hook — occasional pruning. Doesn't run full prune every tick."""
    # Use lightweight day-boundary check: prune once per hour of ticks
    now = datetime.now(UTC)
    if now.minute == 0 and now.second < 30:
        dropped = prune_old_records()
        return {"pruned": dropped}
    return {"pruned": 0}


def build_outcome_learning_surface() -> dict[str, Any]:
    items = _load()
    now = datetime.now(UTC)
    # Compute active-evidence signal (sum of decayed weights)
    total_strength = 0.0
    outcome_counter: dict[str, float] = {}
    for i in items:
        f = _decay_factor(str(i.get("recorded_at")), now)
        w = float(i.get("weight") or 1.0) * f
        total_strength += w
        oc = str(i.get("outcome") or "")
        outcome_counter[oc] = outcome_counter.get(oc, 0.0) + w
    top = top_patterns(limit=5)
    return {
        "active": len(items) > 0,
        "total_records": len(items),
        "total_decayed_strength": round(total_strength, 3),
        "half_life_days": _HALF_LIFE_DAYS,
        "outcome_distribution": {k: round(v, 3) for k, v in outcome_counter.items()},
        "top_patterns": top,
        "summary": _summary_line(len(items), total_strength, top),
    }


def _summary_line(count: int, total: float, top: list[dict[str, Any]]) -> str:
    if count == 0:
        return "Ingen outcome-observationer endnu"
    head = top[0] if top else None
    if head:
        return (
            f"{count} observationer, aktivt signal={round(total, 1)}; "
            f"stærkeste: {head['context']}={head['strength']}"
        )
    return f"{count} observationer, aktivt signal={round(total, 1)}"
