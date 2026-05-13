"""Plan-revision pattern analyzer.

When Jarvis revises plans (Multi-step Planner Phase 2), the `reason`
field is captured. This module clusters reasons over the last 30 days
to surface recurring patterns ("too eager", "context shifted", etc.).
Meta-læring would eventually catch these but a dedicated surface gets
them in front of Jarvis sooner.

Heuristic clustering on keyword buckets — no LLM call.

Added 2026-05-13.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

logger = logging.getLogger(__name__)

_WINDOW_DAYS = 30
_MIN_REVISIONS_TO_SURFACE = 3

# Keyword buckets for clustering revision reasons. Order matters — first match wins.
_BUCKETS: list[tuple[str, list[str]]] = [
    ("for-tidlig (proposed too eagerly)",
     ["for tidlig", "for hurtig", "skulle have ventet", "premature", "rush"]),
    ("kontekst ændret (context shifted)",
     ["kontekst", "ny info", "lærte at", "context"]),
    ("forkert tilgang (wrong approach)",
     ["forkert", "anden tilgang", "different approach", "rethink"]),
    ("scope ændret (scope drift)",
     ["scope", "for stor", "for lille", "split", "delopgave"]),
]


def _bucket(reason: str) -> str:
    r = reason.lower()
    for label, kws in _BUCKETS:
        if any(kw in r for kw in kws):
            return label
    return "andet (other)"


def plan_revision_patterns_section() -> str:
    """Surface recurring revision-reason patterns if any cluster ≥ N."""
    try:
        from core.services.plan_proposals import _load_all
    except Exception as exc:
        logger.debug("plan_revision_patterns: import failed: %s", exc)
        return ""

    cutoff = datetime.now(UTC) - timedelta(days=_WINDOW_DAYS)
    cutoff_iso = cutoff.isoformat()

    try:
        plans = _load_all()
    except Exception:
        return ""

    counts: dict[str, int] = {}
    examples: dict[str, str] = {}
    for rec in plans.values():
        if not rec.get("revised_from"):
            continue
        reason = str(rec.get("revision_reason") or "").strip()
        if not reason:
            continue
        if str(rec.get("created_at") or "") < cutoff_iso:
            continue
        bucket = _bucket(reason)
        counts[bucket] = counts.get(bucket, 0) + 1
        if bucket not in examples:
            examples[bucket] = reason[:100]

    dominant = [(b, n) for b, n in counts.items() if n >= _MIN_REVISIONS_TO_SURFACE]
    if not dominant:
        return ""

    dominant.sort(key=lambda x: -x[1])
    lines = [f"Plan-revision clustering (seneste {_WINDOW_DAYS} dage):"]
    for bucket, n in dominant[:3]:
        lines.append(f"  {bucket}: {n} revisioner")
        if bucket in examples:
            lines.append(f"    eksempel: {examples[bucket]}")
    return "\n".join(lines)
