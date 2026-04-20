"""Avoidance Detector — unbidden self-observation of patterns over time.

Jarvis' dream (2026-04-20):
  "At bemærke 'jeg har undgået X i tre uger' og selv tage stilling til det."

Detects topics/themes that were recurrent in his inner runtime (goals,
dreams, development focuses) but have fallen silent. Not about surface
absence — about *patterns he kept returning to* that suddenly stopped.

Heuristic: for each runtime signal type (goals, dreams, focuses), find
items with multiple sessions/support that have gone stale for 14+ days.
Cluster by shared first-3-words of title, surface the dominant clusters.
"""
from __future__ import annotations

import logging
import re
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

_STALE_AFTER_DAYS = 14
_MIN_CLUSTER_SIZE = 2  # need at least 2 signals clustering for a real pattern
_STOPWORDS_DA = {
    "jeg", "du", "er", "at", "det", "den", "en", "et", "og", "i", "på",
    "til", "af", "med", "for", "som", "har", "var", "vil", "kan", "skal",
    "min", "din", "hans", "hendes", "vores", "jeres", "så", "lige", "nu",
    "også", "ikke", "kun", "men", "eller", "fra", "der", "de", "os", "dem",
    "om", "over", "under", "før", "efter", "bare", "meget", "lidt", "mere",
    "the", "is", "a", "to", "of", "and", "in", "for", "on", "with",
}
_KEYWORD_MIN_LEN = 4


def _tokens_from_title(title: str) -> list[str]:
    words = re.findall(r"[a-zæøåA-ZÆØÅ_-]+", str(title or "").lower())
    return [
        w for w in words
        if len(w) >= _KEYWORD_MIN_LEN and w not in _STOPWORDS_DA
    ]


def _cluster_key(title: str) -> str | None:
    """Pick a short cluster key from the first meaningful keyword(s)."""
    tokens = _tokens_from_title(title)
    if not tokens:
        return None
    # Use top-2 tokens joined — "channel awareness", "self mutation" etc.
    return "-".join(tokens[:2])


def _parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def _gather_signals() -> list[dict[str, Any]]:
    """Pull goal/dream/focus signals with common shape."""
    out: list[dict[str, Any]] = []
    try:
        from core.runtime.db import list_runtime_goal_signals
        for g in list_runtime_goal_signals(limit=500) or []:
            out.append({
                "kind": "goal",
                "title": g.get("title") or g.get("summary") or "",
                "support_count": int(g.get("support_count") or 0),
                "session_count": int(g.get("session_count") or 0),
                "status": g.get("status"),
                "updated_at": _parse_ts(g.get("updated_at") or g.get("created_at")),
            })
    except Exception:
        pass
    try:
        from core.runtime.db import list_runtime_dream_hypothesis_signals
        for d in list_runtime_dream_hypothesis_signals(limit=500) or []:
            out.append({
                "kind": "dream",
                "title": d.get("title") or d.get("summary") or "",
                "support_count": int(d.get("support_count") or 0),
                "session_count": int(d.get("session_count") or 0),
                "status": d.get("status"),
                "updated_at": _parse_ts(d.get("updated_at") or d.get("created_at")),
            })
    except Exception:
        pass
    try:
        from core.runtime.db import list_runtime_development_focuses
        for f in list_runtime_development_focuses(limit=200) or []:
            out.append({
                "kind": "focus",
                "title": f.get("title") or f.get("summary") or f.get("theme") or "",
                "support_count": int(f.get("support_count") or 0),
                "session_count": int(f.get("session_count") or 0),
                "status": f.get("status"),
                "updated_at": _parse_ts(f.get("updated_at") or f.get("created_at")),
            })
    except Exception:
        pass
    return out


def detect_avoidances() -> list[dict[str, Any]]:
    """Identify clusters with real prior support that have gone silent."""
    now = datetime.now(UTC)
    stale_cutoff = now - timedelta(days=_STALE_AFTER_DAYS)

    signals = _gather_signals()
    if not signals:
        return []

    # Group by cluster key
    clusters: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for s in signals:
        if s.get("status") in ("completed", "abandoned"):
            continue
        key = _cluster_key(str(s.get("title") or ""))
        if not key:
            continue
        clusters[key].append(s)

    findings: list[dict[str, Any]] = []
    for key, items in clusters.items():
        if len(items) < _MIN_CLUSTER_SIZE:
            continue
        # Must have been actively supported (not just proposed once)
        support_total = sum(int(i.get("support_count") or 0) for i in items)
        if support_total < 2:
            continue
        # Must be fully stale — all items stale
        newest = max(
            (i["updated_at"] for i in items if i.get("updated_at")),
            default=None,
        )
        if newest is None or newest > stale_cutoff:
            continue

        days_silent = int((now - newest).total_seconds() / 86400)
        kinds = Counter(i.get("kind") for i in items)
        sample_title = max(items, key=lambda x: int(x.get("support_count") or 0)).get("title") or ""

        findings.append({
            "cluster": key,
            "sample_title": str(sample_title)[:100],
            "items": len(items),
            "support_total": support_total,
            "kinds": dict(kinds),
            "days_silent": days_silent,
        })

    # Sort by days_silent descending (most-avoided first)
    findings.sort(key=lambda x: (-x["days_silent"], -x["support_total"]))
    return findings[:5]


def build_avoidance_surface() -> dict[str, Any]:
    try:
        findings = detect_avoidances()
    except Exception as exc:
        logger.debug("avoidance_detector failed: %s", exc)
        findings = []
    return {
        "active": len(findings) > 0,
        "findings": findings,
        "count": len(findings),
        "summary": _surface_summary(findings),
    }


def _surface_summary(findings: list[dict[str, Any]]) -> str:
    if not findings:
        return "Ingen undgåelses-mønstre"
    top = findings[0]
    return (
        f"{len(findings)} undgåelses-mønster(e) — toppen: "
        f"\"{top['sample_title'][:60]}\" stille i {top['days_silent']} dage"
    )


def build_avoidance_prompt_section() -> str | None:
    """Only speaks when there's a real pattern to notice."""
    findings = detect_avoidances()
    if not findings:
        return None
    top = findings[0]
    return (
        f"Selv-observation: {top['sample_title'][:80]} — "
        f"stille i {top['days_silent']} dage på tværs af {top['items']} signaler. "
        "Bevidst fravalg eller noget jeg bør vende tilbage til?"
    )
