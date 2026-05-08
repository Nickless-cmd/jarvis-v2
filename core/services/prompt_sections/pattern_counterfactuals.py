"""Surface pattern-counterfactual hypotheses in the prompt.

Reads the most recent ``counterfactual.pattern_what_if`` events
(written by ``pattern_counterfactual_daemon``) and renders one or two
of them as a "hvad hvis"-block in awareness. Lets Jarvis carry a
felt sense of what his own habits *do* for him by surfacing the
hypothetical absence.

Renders nothing if no fresh counterfactuals exist. TTL-cached.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime, timedelta

from core.runtime.db import connect

logger = logging.getLogger(__name__)

_FRESHNESS_HOURS = 24  # show counterfactuals at most 24h old
_MAX_TO_SHOW = 2

_CACHE_TTL_SECONDS = 1800.0  # 30 min — these change at the daemon's hourly cadence
_cached_text: str | None = None
_cached_at: float = 0.0


def _fetch_recent_counterfactuals() -> list[dict]:
    cutoff = (datetime.now(UTC) - timedelta(hours=_FRESHNESS_HOURS)).isoformat()
    with connect() as c:
        rows = c.execute(
            "SELECT payload_json FROM events "
            "WHERE kind = 'counterfactual.pattern_what_if' "
            "AND created_at >= ? "
            "ORDER BY id DESC LIMIT ?",
            (cutoff, _MAX_TO_SHOW * 3),  # over-fetch, dedupe by pattern below
        ).fetchall()
    out: list[dict] = []
    seen_patterns: set[tuple[str, str]] = set()
    for r in rows:
        try:
            p = json.loads(r["payload_json"] or "{}")
        except Exception:
            continue
        key = (p.get("parent_kind", ""), p.get("child_kind", ""))
        if not all(key) or key in seen_patterns:
            continue
        seen_patterns.add(key)
        out.append(p)
        if len(out) >= _MAX_TO_SHOW:
            break
    return out


def pattern_counterfactuals_section() -> str:
    """Build awareness section from recent pattern counterfactuals."""
    global _cached_text, _cached_at
    now = time.monotonic()
    if _cached_text is not None and (now - _cached_at) < _CACHE_TTL_SECONDS:
        return _cached_text

    try:
        items = _fetch_recent_counterfactuals()
    except Exception as exc:
        logger.debug("pattern_counterfactuals: fetch failed: %s", exc)
        _cached_text = ""
        _cached_at = now
        return ""

    if not items:
        _cached_text = ""
        _cached_at = now
        return ""

    lines = ["🔮 Hvad hvis dette mønster stoppede:"]
    for it in items:
        pk = it.get("parent_kind", "?")
        ck = it.get("child_kind", "?")
        n = int(it.get("occurrences_7d") or 0)
        hypothesis = str(it.get("hypothesis") or "").strip()
        if not hypothesis:
            continue
        lines.append(f"  · {pk} → {ck} ({n}× sidste uge):")
        lines.append(f"    {hypothesis}")

    text = "\n".join(lines) if len(lines) > 1 else ""
    _cached_text = text
    _cached_at = now
    return text


def invalidate_cache() -> None:
    global _cached_text, _cached_at
    _cached_text = None
    _cached_at = 0.0
