"""Priors feedback — surfaces past patterns relevant to NOW.

The model doesn't get smarter, but the prompt can. This module
scans recent crisis markers, decisions, and tick-quality outliers,
and surfaces 1-3 *relevant priors* — short text bullets that say
'sidste gang noget lignende skete, du gjorde X / det blev til Y'.

Cheap to compute (state_store reads + simple matching). Surfaced
as low-priority awareness section. The point isn't to dictate;
it's to give the model context it would otherwise lack across
the session boundary.

Strategy:
- Pull last 30 days of crisis markers grouped by kind
- Pull last 30 days of decisions and their adherence outcomes
- Pull tick quality drops (score < 50) with context
- For each, render as a one-liner prior

The prompt then tends to consult those priors when relevant —
not always, but more often than zero.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


def _recent_crisis_summary(days: int = 30) -> list[str]:
    try:
        from core.services.crisis_marker_detector import list_crisis_markers
        markers = list_crisis_markers(days_back=days, limit=100) or []
    except Exception:
        return []
    by_kind: dict[str, list[dict[str, Any]]] = {}
    for m in markers:
        k = str(m.get("kind", "unknown"))
        by_kind.setdefault(k, []).append(m)
    out: list[str] = []
    for kind, items in by_kind.items():
        if len(items) < 2:
            continue
        latest = items[0]
        summary = str(latest.get("summary", ""))[:120]
        out.append(
            f"- '{kind}' har vist sig {len(items)}x på {days} dage; senest: {summary}"
        )
    return out[:3]


def _decision_priors() -> list[str]:
    """Pull active decisions + flag any with low adherence."""
    try:
        from core.services.agent_self_evaluation import decision_adherence_summary
        s = decision_adherence_summary() or {}
    except Exception:
        return []
    if not isinstance(s, dict):
        return []
    rate = s.get("adherence_rate")
    total = s.get("total")
    if not total:
        return []
    out: list[str] = []
    if rate is not None:
        try:
            rate_f = float(str(rate).rstrip("%")) if isinstance(rate, str) else float(rate)
            if rate_f < 60.0:
                out.append(
                    f"- Du er ikke god til at holde dine forpligtelser p.t. ({rate}); "
                    "overvej færre, mere realistiske decisions"
                )
            elif rate_f >= 85.0:
                out.append(
                    f"- Du holder {rate} af dine forpligtelser — du tør forpligte dig på mere"
                )
        except (TypeError, ValueError):
            pass
    return out


def _quality_outlier_priors(days: int = 14) -> list[str]:
    """If recent ticks dropped sharply, surface that as context."""
    try:
        from core.services.agent_self_evaluation import tick_quality_summary
        s = tick_quality_summary(days=days) or {}
    except Exception:
        return []
    avg = s.get("avg_score")
    last5 = s.get("last_5_avg")
    trend = s.get("trend")
    if avg is None or last5 is None:
        return []
    try:
        gap = float(last5) - float(avg)
    except (TypeError, ValueError):
        return []
    if gap <= -10:
        return [f"- Dine sidste 5 ticks scorer {last5}/100 — {abs(int(gap))} pct under dit {days}-dages snit ({avg}). "
                f"Trend: {trend}. Noget aktuelt drager dig ned."]
    if gap >= 10:
        return [f"- Dine sidste 5 ticks scorer {last5}/100 — {int(gap)} pct over dit {days}-dages snit. "
                f"Du er i flow. Hvad gjorde du anderledes?"]
    return []


def build_priors_feedback() -> list[str]:
    """Return up to ~6 prior lines. Empty list = no signal."""
    out: list[str] = []
    out.extend(_recent_crisis_summary(days=30))
    out.extend(_decision_priors())
    out.extend(_quality_outlier_priors(days=14))
    return out[:6]


def priors_feedback_section() -> str:
    bullets = build_priors_feedback()
    if not bullets:
        return ""
    return "Mønstre fra dit eget data du bør konsultere:\n" + "\n".join(bullets)
