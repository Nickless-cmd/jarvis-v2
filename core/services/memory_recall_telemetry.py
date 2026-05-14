"""Memory recall telemetry — Phase 2 data collection for Lag 11 forgetting.

Per the 2026-05-10 true-forgetting spec, Phase 2 (recall-failure detection)
correlates `memory.recall_empty` events against `absence_traces.month_key`
to find patterns where Jarvis searches near memories that have faded.

The spec said Phase 2 builds when Phase 1 has 30 days of data. Phase 1
shipped 2026-05-10 (4 days ago) — too early for the correlation daemon.
But the eventbus emission can land NOW, so the 30-day clock starts
ticking immediately rather than from whenever Phase 2 actually starts.

This module:

1. ``emit_recall_empty(tool, query, workspace_id=None)`` — fire-and-forget
   event publisher for the empty-results branch of memory-search tools.
   Used by _exec_search_memory, _exec_search_chat_history,
   exec_search_sessions.

2. ``count_recent_recall_empty(hours=24)`` — read-only aggregator for MC
   visibility (how many empty searches in the last N hours, optionally
   grouped by tool).

The actual Phase 2 correlation daemon will read the events table directly,
joining `memory.recall_empty` with `absence_traces` on month_key. That
daemon is out of scope here — this module just plants the seed.

Added 2026-05-14.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


def emit_recall_empty(
    *,
    tool: str,
    query: str,
    workspace_id: str | None = None,
) -> None:
    """Publish a memory.recall_empty event. Best-effort — never raises.

    The event payload is intentionally minimal: just enough for the Phase 2
    correlation daemon to detect "searched for X around time Y" patterns.
    No internal state, no PII beyond the query the user/Jarvis already saw.
    """
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            "memory.recall_empty",
            {
                "tool": str(tool or "").strip()[:64],
                "query": str(query or "").strip()[:200],
                "workspace_id": str(workspace_id or "default")[:64],
                "month_key": datetime.now(UTC).strftime("%Y-%m"),
            },
        )
    except Exception as exc:
        logger.debug("memory_recall_telemetry: emit failed: %s", exc)


def count_recent_recall_empty(
    *, hours: int = 24, by_tool: bool = False
) -> dict[str, Any]:
    """Aggregate recall-empty events over the last N hours.

    Returns either a flat count or a per-tool breakdown. Used for MC
    surfaces and for the future Phase 2 correlation daemon. Read-only.
    """
    hours = max(1, min(24 * 30, int(hours)))
    cutoff = (datetime.now(UTC) - timedelta(hours=hours)).isoformat()
    try:
        from core.runtime.db import connect
    except Exception:
        return {"status": "error", "total": 0, "by_tool": {}}

    try:
        with connect() as conn:
            if by_tool:
                rows = conn.execute(
                    "SELECT json_extract(payload_json, '$.tool') AS tool, "
                    "COUNT(*) AS n FROM events "
                    "WHERE kind = 'memory.recall_empty' AND created_at >= ? "
                    "GROUP BY tool ORDER BY n DESC",
                    (cutoff,),
                ).fetchall()
                breakdown = {str(r[0] or "unknown"): int(r[1]) for r in rows}
                total = sum(breakdown.values())
            else:
                row = conn.execute(
                    "SELECT COUNT(*) FROM events "
                    "WHERE kind = 'memory.recall_empty' AND created_at >= ?",
                    (cutoff,),
                ).fetchone()
                breakdown = {}
                total = int(row[0]) if row else 0
    except Exception as exc:
        logger.debug("memory_recall_telemetry: count failed: %s", exc)
        return {"status": "error", "total": 0, "by_tool": {}}

    return {
        "status": "ok",
        "window_hours": hours,
        "total": total,
        "by_tool": breakdown,
    }


def build_memory_recall_telemetry_surface() -> dict[str, object]:
    """MC surface — read-only meta-projection."""
    s = count_recent_recall_empty(hours=24, by_tool=True)
    return {
        "active": True,
        "mode": "memory_recall_telemetry",
        "summary": (
            f"{s.get('total', 0)} recall-empty events in last 24h "
            f"(across {len(s.get('by_tool', {}))} tools)"
        ),
        "stats": s,
        "authority": "derived-read-only",
    }


def _emit_memory_recall_telemetry_event(
    kind: str, payload: dict[str, object] | None = None
) -> None:
    """Defensive scoped event emitter."""
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(f"memory_recall_telemetry.{kind}", payload or {})
    except Exception:
        pass
