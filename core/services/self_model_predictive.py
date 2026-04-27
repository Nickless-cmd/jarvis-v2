"""Predictive self-model — frequencies, not aspirations.

runtime_self_model.py describes who Jarvis *says* he is. This module
describes who he *empirically* is, based on tracked signals:

- Tick quality distribution: avg, p50, p90 over last N days
- Mood baseline by dimension: mean + stdev
- Decision adherence: % kept vs revoked
- Crisis frequency: how often, what kind
- Productive idle ratio: % of ticks that recovered fatigue

These numbers turn the self-model from an aspiration ("I am curious")
into a prediction ("In 73% of recent ticks, my curiosity > 0.55").

When the empirical model diverges from the aspirational one, that IS
information — either his actual behavior has shifted, or the
aspiration was inaccurate.

Output: dict that can be rendered as prompt section. Cheap to compute
(reads state_store + recent jobs). Cached briefly per call.
"""
from __future__ import annotations

import logging
import statistics
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


def _tick_quality_stats(days: int = 14) -> dict[str, Any]:
    try:
        from core.services.agent_self_evaluation import tick_quality_summary
        s = tick_quality_summary(days=days)
        if s.get("count", 0) < 3:
            return {}
        return {
            "avg": s.get("avg_score"),
            "last_5_avg": s.get("last_5_avg"),
            "trend": s.get("trend"),
            "samples": s.get("count"),
        }
    except Exception:
        return {}


def _mood_baseline(days: int = 14) -> dict[str, dict[str, Any]]:
    try:
        from core.services.personality_drift import compute_baseline
        return compute_baseline(lookback_days=days) or {}
    except Exception:
        return {}


def _decision_adherence() -> dict[str, Any]:
    try:
        from core.services.agent_self_evaluation import decision_adherence_summary
        return decision_adherence_summary() or {}
    except Exception:
        return {}


def _crisis_frequency(days: int = 30) -> dict[str, Any]:
    try:
        from core.services.crisis_marker_detector import list_crisis_markers
        markers = list_crisis_markers(days_back=days, limit=200) or []
    except Exception:
        markers = []
    if not markers:
        return {"count": 0, "per_week": 0.0, "by_kind": {}}
    by_kind: dict[str, int] = {}
    for m in markers:
        k = str(m.get("kind", "unknown"))
        by_kind[k] = by_kind.get(k, 0) + 1
    weeks = max(1.0, days / 7.0)
    return {
        "count": len(markers),
        "per_week": round(len(markers) / weeks, 2),
        "by_kind": by_kind,
    }


def _productive_idle_ratio(days: int = 7) -> float | None:
    """Fraction of ticks that ran productive idle vs all ticks."""
    try:
        from core.runtime.state_store import load_json
        ticks = load_json("recent_ticks", [])
        if not isinstance(ticks, list) or not ticks:
            return None
    except Exception:
        return None
    cutoff = datetime.now(UTC) - timedelta(days=days)
    relevant: list[dict[str, Any]] = []
    for t in ticks[-500:]:
        if not isinstance(t, dict):
            continue
        ts = str(t.get("at", ""))
        try:
            if datetime.fromisoformat(ts) < cutoff:
                continue
        except ValueError:
            continue
        relevant.append(t)
    if not relevant:
        return None
    productive = sum(1 for t in relevant if t.get("productive_idle"))
    return round(productive / len(relevant), 2)


def build_predictive_self_model(days: int = 14) -> dict[str, Any]:
    """Compute the empirical self-model. Cheap; fresh each call."""
    return {
        "window_days": days,
        "tick_quality": _tick_quality_stats(days=days),
        "mood_baseline": _mood_baseline(days=days),
        "adherence": _decision_adherence(),
        "crisis_frequency_30d": _crisis_frequency(days=30),
        "productive_idle_ratio_7d": _productive_idle_ratio(days=7),
    }


def predictive_self_model_section() -> str:
    """Render predictive self-model as a prompt awareness section."""
    m = build_predictive_self_model(days=14)
    lines: list[str] = ["Hvem du *empirisk* er (sidste 14 dage):"]

    tq = m.get("tick_quality") or {}
    if tq:
        lines.append(
            f"- Tick-kvalitet: {tq.get('avg')}/100 (n={tq.get('samples')}, "
            f"trend: {tq.get('trend')}, sidste 5: {tq.get('last_5_avg')})"
        )

    mood = m.get("mood_baseline") or {}
    if mood:
        salient: list[str] = []
        for dim, info in sorted(mood.items()):
            if not isinstance(info, dict):
                continue
            mean = info.get("mean")
            stdev = info.get("stdev")
            if mean is None:
                continue
            stable = "stabil" if (stdev or 0) < 0.1 else "varierende"
            try:
                salient.append(f"{dim}={float(mean):.2f} ({stable})")
            except (TypeError, ValueError):
                continue
        if salient:
            lines.append("- Stemnings-baseline: " + ", ".join(salient[:5]))

    adh = m.get("adherence") or {}
    if isinstance(adh, dict) and adh.get("total"):
        rate = adh.get("adherence_rate")
        flag = adh.get("flag")
        bit = f"- Beslutnings-adherence: {rate} ({adh.get('total')} forpligtelser)"
        if flag:
            bit += f" ⚠ {flag}"
        lines.append(bit)

    cf = m.get("crisis_frequency_30d") or {}
    if cf.get("count"):
        kinds = ", ".join(f"{k}:{v}" for k, v in (cf.get("by_kind") or {}).items())
        lines.append(
            f"- Kriser sidste 30 dage: {cf.get('count')} ({cf.get('per_week')}/uge) — {kinds}"
        )

    pi = m.get("productive_idle_ratio_7d")
    if pi is not None:
        lines.append(f"- Produktivt idle-forhold (7d): {pi}")

    if len(lines) == 1:
        return ""  # no signal yet
    return "\n".join(lines)
