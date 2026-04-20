"""Relation Dynamics — pattern-recognition on people, not just facts.

Jarvis' PLAN_WILD_IDEAS #10 (2026-04-20): extend user knowledge with
automatic dynamic observations — time-patterns, topic-patterns, stress
signals — and a warmth/engagement trend per relation.

Transparent: all observations stored in workspace runtime state (visible
in MC) and tagged with [auto-obs] if written back into USER.md. The
write-back is optional and rate-limited.
"""
from __future__ import annotations

import json
import logging
import os
import re
import statistics
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_STORAGE_REL = "workspaces/default/runtime/relation_dynamics.json"
_RECOMPUTE_SECONDS = 30 * 60
_USER_ID = "bjorn"  # primary relation (the owner)

_last_computed_ts: float = 0.0
_cached: dict[str, Any] = {}


def _storage_path() -> Path:
    base = os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2")
    return Path(base) / _STORAGE_REL


def _load() -> dict[str, Any]:
    path = _storage_path()
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception as exc:
        logger.warning("relation_dynamics: load failed: %s", exc)
    return {}


def _save(data: dict[str, Any]) -> None:
    path = _storage_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(path)
    except Exception as exc:
        logger.warning("relation_dynamics: save failed: %s", exc)


def _recent_runs(days: int = 14, limit: int = 500) -> list[dict[str, Any]]:
    try:
        from core.runtime.db import recent_visible_runs
        runs = recent_visible_runs(limit=limit) or []
    except Exception:
        return []
    cutoff = datetime.now(UTC) - timedelta(days=days)
    filtered: list[dict[str, Any]] = []
    for r in runs:
        ts = str(r.get("started_at") or "")
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except Exception:
            continue
        if dt >= cutoff:
            r = dict(r)
            r["_parsed_at"] = dt
            filtered.append(r)
    return filtered


def _time_patterns(runs: list[dict[str, Any]]) -> dict[str, Any]:
    hour_counts: Counter[int] = Counter()
    for r in runs:
        hour_counts[r["_parsed_at"].hour] += 1
    if not hour_counts:
        return {}
    total = sum(hour_counts.values())
    top_hours = sorted(hour_counts.items(), key=lambda kv: kv[1], reverse=True)[:5]
    top_hours_pct = [
        {"hour": h, "count": c, "share": round(c / total, 3)} for h, c in top_hours
    ]
    # Peak window detection: find 3-hour block with highest density
    best_start = 0
    best_sum = 0
    for start in range(24):
        s = sum(hour_counts.get((start + i) % 24, 0) for i in range(3))
        if s > best_sum:
            best_sum = s
            best_start = start
    peak_window = f"{best_start:02d}-{(best_start + 3) % 24:02d}"
    return {
        "top_hours": top_hours_pct,
        "peak_window": peak_window,
        "peak_window_count": best_sum,
    }


_WORD_RE = re.compile(r"[a-zæøåA-ZÆØÅ_-]+")
_STOPWORDS = {
    "jeg", "du", "er", "at", "det", "den", "en", "et", "og", "i", "på",
    "til", "af", "med", "for", "som", "har", "var", "vil", "kan", "skal",
    "nu", "ikke", "også", "lige", "men", "eller", "fra",
    "the", "is", "a", "to", "of", "and", "in", "for",
}


def _topic_patterns(runs: list[dict[str, Any]]) -> dict[str, Any]:
    word_counts: Counter[str] = Counter()
    for r in runs:
        text = str(r.get("text_preview") or "")[:400].lower()
        words = [w for w in _WORD_RE.findall(text) if len(w) >= 5 and w not in _STOPWORDS]
        word_counts.update(words)
    top = word_counts.most_common(10)
    return {"top_terms": [{"term": t, "count": c} for t, c in top]}


def _message_length_stats(runs: list[dict[str, Any]]) -> dict[str, Any]:
    lengths: list[int] = []
    for r in runs:
        t = str(r.get("text_preview") or "")
        lengths.append(len(t))
    if not lengths:
        return {}
    return {
        "avg_preview_length": round(statistics.mean(lengths), 1),
        "median_preview_length": round(statistics.median(lengths), 1),
        "short_message_ratio": round(sum(1 for l in lengths if l < 40) / len(lengths), 3),
    }


def _engagement_trend(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare last-week run count vs previous-week."""
    if not runs:
        return {"trend": "unknown"}
    now = datetime.now(UTC)
    last_week = sum(1 for r in runs if (now - r["_parsed_at"]) <= timedelta(days=7))
    prev_week = sum(
        1 for r in runs
        if timedelta(days=7) < (now - r["_parsed_at"]) <= timedelta(days=14)
    )
    if prev_week == 0 and last_week == 0:
        return {"trend": "dormant", "last_week": 0, "prev_week": 0}
    if prev_week == 0:
        return {"trend": "new-activity", "last_week": last_week, "prev_week": 0}
    delta = last_week - prev_week
    pct = delta / prev_week
    if pct > 0.2:
        trend = "rising"
    elif pct < -0.2:
        trend = "cooling"
    else:
        trend = "stable"
    return {
        "trend": trend,
        "last_week": last_week,
        "prev_week": prev_week,
        "delta_pct": round(pct, 3),
    }


def _warmth_from_sources() -> float | None:
    """Pull trust-trajectory tail from relationship_texture as warmth proxy."""
    try:
        from core.runtime.db import get_latest_cognitive_relationship_texture
        tx = get_latest_cognitive_relationship_texture() or {}
        trust_raw = tx.get("trust_trajectory") or "[]"
        trust = json.loads(trust_raw) if isinstance(trust_raw, str) else list(trust_raw)
        tail = trust[-10:] if trust else []
        if not tail:
            return None
        return round(float(statistics.mean(tail)), 3)
    except Exception:
        return None


def _vibe_from_recent(runs: list[dict[str, Any]]) -> str | None:
    if not runs:
        return None
    # Look at most recent run
    latest = max(runs, key=lambda r: r["_parsed_at"])
    text = str(latest.get("text_preview") or "").lower()
    if not text:
        return None
    if any(w in text for w in ("tak", "elsker", "smukt", "dejligt", "❤")):
        return "warm"
    if any(w in text for w in ("nej", "forkert", "stop", "ikke", "ikk")):
        return "corrective"
    if len(text) < 40:
        return "short"
    return "engaged"


def _recompute() -> dict[str, Any]:
    runs = _recent_runs()
    payload = {
        "computed_at": datetime.now(UTC).isoformat(),
        "relation_id": _USER_ID,
        "warmth": _warmth_from_sources(),
        "engagement_trend": _engagement_trend(runs),
        "time_patterns": _time_patterns(runs),
        "topic_patterns": _topic_patterns(runs),
        "message_length_stats": _message_length_stats(runs),
        "last_interaction_vibe": _vibe_from_recent(runs),
        "runs_considered": len(runs),
    }
    _save(payload)
    return payload


def get_relation_dynamics() -> dict[str, Any]:
    global _cached, _last_computed_ts
    now_ts = datetime.now(UTC).timestamp()
    if not _cached or (now_ts - _last_computed_ts) > _RECOMPUTE_SECONDS:
        try:
            _cached = _recompute()
        except Exception as exc:
            logger.debug("relation_dynamics recompute failed: %s", exc)
            _cached = _load() or {}
        _last_computed_ts = now_ts
    return dict(_cached)


def tick(_seconds: float = 0.0) -> dict[str, Any]:
    r = get_relation_dynamics()
    return {
        "warmth": r.get("warmth"),
        "trend": (r.get("engagement_trend") or {}).get("trend"),
    }


def build_relation_dynamics_surface() -> dict[str, Any]:
    r = get_relation_dynamics()
    et = r.get("engagement_trend") or {}
    tp = r.get("time_patterns") or {}
    return {
        "active": bool(r),
        "relation_id": r.get("relation_id"),
        "warmth": r.get("warmth"),
        "engagement_trend": et.get("trend"),
        "engagement_last_week": et.get("last_week"),
        "engagement_prev_week": et.get("prev_week"),
        "peak_window": tp.get("peak_window"),
        "top_terms": (r.get("topic_patterns") or {}).get("top_terms") or [],
        "last_interaction_vibe": r.get("last_interaction_vibe"),
        "message_length_stats": r.get("message_length_stats"),
        "runs_considered": r.get("runs_considered"),
        "computed_at": r.get("computed_at"),
        "summary": _surface_summary(r),
    }


def _surface_summary(r: dict[str, Any]) -> str:
    if not r:
        return "Relation-dynamik endnu ikke beregnet"
    et = r.get("engagement_trend") or {}
    tp = r.get("time_patterns") or {}
    trend = et.get("trend")
    peak = tp.get("peak_window")
    warmth = r.get("warmth")
    vibe = r.get("last_interaction_vibe")
    parts = []
    if warmth is not None:
        parts.append(f"warmth={warmth}")
    if trend:
        parts.append(f"trend={trend}")
    if peak:
        parts.append(f"peak={peak}")
    if vibe:
        parts.append(f"vibe={vibe}")
    return ", ".join(parts) if parts else "beregner..."


def build_relation_dynamics_prompt_section() -> str | None:
    """Surface only when trend is noteworthy (rising, cooling, dormant)."""
    r = get_relation_dynamics()
    et = r.get("engagement_trend") or {}
    trend = str(et.get("trend") or "")
    if trend in ("stable", "new-activity", "unknown", ""):
        return None
    if trend == "rising":
        return f"Relation: stigende engagement ({et.get('last_week')} runs sidste uge vs {et.get('prev_week')})."
    if trend == "cooling":
        return f"Relation: afkølende engagement ({et.get('last_week')} vs {et.get('prev_week')}). Mærk efter hvorfor."
    if trend == "dormant":
        return "Relation: ingen aktivitet de sidste 2 uger."
    return None
