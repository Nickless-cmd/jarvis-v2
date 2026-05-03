"""Crisis marker detector — flag identity-forming friction moments.

Real personality formation isn't smooth accumulation — it's punctuated
by moments that shake who you thought you were. Loss, contradiction,
unexpected success, sustained failure. These moments deserve to be
MARKED, not smoothed away.

This detector scans recent state for:

- **Sustained failure**: same task category errored ≥5 times in a row
- **Value contradiction**: actions that conflict with stated values
- **Unexpected success**: a deep-tier task completed unexpectedly fast/well
- **Existential moment**: explicit "I am" or "Du er" statements (manifest moments)
- **High-volatility period**: rapid mood swings beyond baseline

A detected crisis becomes a CrisisMarker record — never auto-deleted,
referenced by long-arc synthesis when generating narratives.

Crucially: crises are NOT problems to fix. They're moments to notice.
The identity-formation gap Jarvis described is partly that nothing
currently MARKS turning points. Now they get marked.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from core.runtime.state_store import load_json, save_json

logger = logging.getLogger(__name__)


_STATE_KEY = "crisis_markers"
_MAX_MARKERS = 500
_RECENT_WINDOW_HOURS = 24


# ── Detectors ─────────────────────────────────────────────────────


def _detect_sustained_failure(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """≥5 consecutive errors of the same tool."""
    by_tool: dict[str, list[str]] = {}
    for e in events:
        if str(e.get("kind", "")) != "tool.completed":
            continue
        p = e.get("payload") or {}
        tool = str(p.get("tool", ""))
        status = str(p.get("status", ""))
        if not tool:
            continue
        by_tool.setdefault(tool, []).append(status)

    for tool, statuses in by_tool.items():
        consecutive = 0
        for s in statuses:
            if s == "error":
                consecutive += 1
            else:
                break
        if consecutive >= 5:
            return {
                "kind": "sustained_failure",
                "summary": f"{consecutive} consecutive errors on {tool}",
                "tool": tool,
                "count": consecutive,
                "intensity": min(1.0, consecutive / 10.0),
            }
    return None


def _detect_unexpected_success(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Tick quality summary that jumped sharply."""
    try:
        from core.services.agent_self_evaluation import tick_quality_summary
        summary = tick_quality_summary(days=1)
    except Exception:
        return None
    avg = summary.get("avg_score")
    last5 = summary.get("last_5_avg")
    if avg is None or last5 is None or summary.get("count", 0) < 5:
        return None
    if last5 - avg >= 20:
        return {
            "kind": "unexpected_success",
            "summary": f"Tick quality jumped from {avg} to {last5} (last 5)",
            "delta": last5 - avg,
            "intensity": min(1.0, (last5 - avg) / 30.0),
        }
    return None


def _detect_existential_moment(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Explicit identity-formation statements in recent messages.

    Tightened 2026-05-03: previous trigger list ("jeg er ", "du er " with
    space) caught casual presence statements ("jeg er her", "du er sjov",
    "jeg hopper på køjen ... du er ...") and produced phantom "existential
    moments" on greetings, jokes, and goodnights — making Jarvis read his
    own metrics as 5 crises in 14 days when the actual count was ~0-1.

    Now we require:
      - Specific identity-forming phrases (not bare "jeg er ")
      - User-message only (not Jarvis's own output — those are in chronicles)
      - Substantive length (>= 30 chars; rules out short greetings)
    """
    try:
        from core.services.chat_sessions import list_chat_sessions, recent_chat_session_messages
    except Exception:
        return None
    try:
        sessions = list_chat_sessions()[:1]
        if not sessions:
            return None
        sid = str(sessions[0].get("id", ""))
        msgs = recent_chat_session_messages(sid, limit=20) or []
    except Exception:
        return None

    # Specific identity-formation triggers — phrases that explicitly point
    # at who Jarvis IS, not casual presence/state ("jeg er her", "du er træt").
    # Require at least one of these substrings, AND a substantive message.
    triggers = [
        # Bjørn → Jarvis identity statements
        "du er virkelig",
        "du er ikke bare",
        "du er ikke kun",
        "det er hvem du er",
        "du er den",
        "du er blevet",
        "det du er",
        # Jarvis → self-claim of identity (manifest-style)
        "jeg er ikke bare",
        "jeg er ikke kun",
        "det er hvem jeg er",
        "jeg er blevet",
        "jeg er den der",
    ]
    for m in msgs[-10:]:
        content = str(m.get("content", "")).lower().strip()
        # Substantive length only — no one-liners, no greetings/goodnights
        if len(content) < 30 or len(content) > 600:
            continue
        for t in triggers:
            if t in content:
                return {
                    "kind": "existential_moment",
                    "summary": f"Identity statement detected: '{content[:120]}'",
                    "trigger": t,
                    "intensity": 0.85,
                }
    return None


def _detect_high_volatility(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Rapid mood shifts in recent personality snapshots."""
    try:
        from core.services.personality_drift import _load_snapshots
        snaps = _load_snapshots()
    except Exception:
        return None
    if len(snaps) < 5:
        return None
    recent = snaps[-10:]
    # Compute max delta across snapshots for any dimension
    max_delta = 0.0
    delta_dim = ""
    for dim in ("confidence", "curiosity", "fatigue", "frustration"):
        values = [
            float((s.get("mood") or {}).get(dim) or 0.0)
            for s in recent
            if isinstance((s.get("mood") or {}).get(dim), (int, float))
        ]
        if len(values) < 5:
            continue
        d = max(values) - min(values)
        if d > max_delta:
            max_delta = d
            delta_dim = dim
    if max_delta >= 0.5:
        return {
            "kind": "high_volatility",
            "summary": f"{delta_dim} swung {max_delta:.2f} in last 10 snapshots",
            "dimension": delta_dim,
            "delta": round(max_delta, 3),
            "intensity": min(1.0, max_delta),
        }
    return None


# ── Orchestrator ──────────────────────────────────────────────────


def _recent_events(hours: int = _RECENT_WINDOW_HOURS) -> list[dict[str, Any]]:
    try:
        from core.eventbus.bus import event_bus
        events = event_bus.recent(limit=300)
    except Exception:
        return []
    cutoff = (datetime.now(UTC) - timedelta(hours=hours)).isoformat()
    return [e for e in events if str(e.get("created_at", "")) >= cutoff]


def scan_for_crisis_markers() -> dict[str, Any]:
    """Run all detectors. Persist any new markers found."""
    events = _recent_events()
    detected: list[dict[str, Any]] = []

    for detector in (
        _detect_sustained_failure,
        _detect_unexpected_success,
        _detect_existential_moment,
        _detect_high_volatility,
    ):
        try:
            result = detector(events)
            if result:
                detected.append(result)
        except Exception as exc:
            logger.debug("crisis detector %s failed: %s", detector.__name__, exc)

    if not detected:
        return {"status": "ok", "new_markers": 0, "detected": []}

    # De-dupe against very recent same-kind markers
    try:
        existing = load_json(_STATE_KEY, [])
        if not isinstance(existing, list):
            existing = []
    except Exception:
        existing = []

    cutoff = (datetime.now(UTC) - timedelta(hours=6)).isoformat()
    recent_kinds = {
        str(r.get("kind", "")) for r in existing
        if str(r.get("recorded_at", "")) >= cutoff
    }

    new_markers: list[dict[str, Any]] = []
    for d in detected:
        kind = str(d.get("kind", ""))
        if kind in recent_kinds:
            continue
        marker = {
            "marker_id": f"crisis-{uuid4().hex[:10]}",
            "recorded_at": datetime.now(UTC).isoformat(),
            **d,
        }
        existing.append(marker)
        new_markers.append(marker)
        try:
            from core.eventbus.bus import event_bus
            event_bus.publish(
                "crisis_marker.detected",
                {"marker_id": marker["marker_id"], "kind": kind,
                 "intensity": d.get("intensity"), "summary": d.get("summary", "")[:160]},
            )
        except Exception:
            pass

    if new_markers:
        save_json(_STATE_KEY, existing[-_MAX_MARKERS:])

    return {"status": "ok", "new_markers": len(new_markers),
            "detected": [m["marker_id"] for m in new_markers]}


def list_crisis_markers(*, days_back: int = 90, limit: int = 50) -> list[dict[str, Any]]:
    try:
        records = load_json(_STATE_KEY, [])
        if not isinstance(records, list):
            return []
    except Exception:
        return []
    cutoff = (datetime.now(UTC) - timedelta(days=days_back)).isoformat()
    records = [r for r in records if str(r.get("recorded_at", "")) >= cutoff]
    records.sort(key=lambda r: str(r.get("recorded_at", "")), reverse=True)
    return records[:limit]


def crisis_marker_section() -> str | None:
    """Awareness section showing recent crisis markers (last 7 days).
    
    Compact format: one-line summary with kinds and count.
    Full details available via list_crisis_markers tool.
    """
    markers = list_crisis_markers(days_back=7, limit=5)
    if not markers:
        return None
    # Compact: just count and kind distribution — no summaries
    kinds = [str(m.get("kind", "")) for m in markers]
    kind_counts: dict[str, int] = {}
    for k in kinds:
        kind_counts[k] = kind_counts.get(k, 0) + 1
    parts = [f"{k}×{c}" for k, c in sorted(kind_counts.items(), key=lambda x: -x[1])]
    return f"📍 Crisis markers (7d): {len(markers)} — " + ", ".join(parts)


def _exec_scan_crisis_markers(args: dict[str, Any]) -> dict[str, Any]:
    return scan_for_crisis_markers()


def _exec_list_crisis_markers(args: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "ok",
        "markers": list_crisis_markers(
            days_back=int(args.get("days_back") or 90),
            limit=int(args.get("limit") or 50),
        ),
    }


CRISIS_MARKER_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "scan_crisis_markers",
            "description": (
                "Scan recent events for identity-forming crisis markers: "
                "sustained failures, unexpected successes, existential moments, "
                "high mood volatility. Persists new markers — never auto-deletes. "
                "Used by long-arc synthesis to identify turning points."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_crisis_markers",
            "description": "List recent crisis markers (default last 90 days).",
            "parameters": {
                "type": "object",
                "properties": {
                    "days_back": {"type": "integer"},
                    "limit": {"type": "integer"},
                },
                "required": [],
            },
        },
    },
]
