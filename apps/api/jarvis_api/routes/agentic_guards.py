"""MC endpoint for agentic-loop guard observability.

Right now exposes one signal: how often the soft tool-only nudge has
fired (from visible_runs.py). Reads agentic.* events from the events
table directly — no separate metric store needed.
"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter

from core.runtime.db import connect

router = APIRouter(prefix="/mc", tags=["mc-agentic-guards"])


def _count_kind_since(kind: str, since_iso: str) -> int:
    with connect() as c:
        row = c.execute(
            "SELECT COUNT(*) AS n FROM events WHERE kind = ? AND created_at >= ?",
            (kind, since_iso),
        ).fetchone()
    return int(row["n"] if row else 0)


def _recent_kind(kind: str, since_iso: str, limit: int = 10) -> list[dict]:
    """Recent fires of a specific event kind (newest first)."""
    import json
    with connect() as c:
        rows = c.execute(
            "SELECT created_at, payload_json FROM events "
            "WHERE kind = ? AND created_at >= ? "
            "ORDER BY id DESC LIMIT ?",
            (kind, since_iso, limit),
        ).fetchall()
    out = []
    for r in rows:
        try:
            payload = json.loads(r["payload_json"] or "{}")
        except Exception:
            payload = {}
        out.append({
            "at": r["created_at"],
            "run_id": payload.get("run_id"),
            "rounds": payload.get("rounds"),
            "decision_id": payload.get("decision_id"),
        })
    return out


@router.get("/agentic-guards-state")
def get_state() -> dict:
    """Counters for agentic-loop guard fires across recent windows.

    Returns:
        {
          "tool_only_nudge_fired": {
            "today": N, "last_24h": N, "last_7d": N,
            "recent_fires": [{at, run_id, rounds, decision_id}, ...]
          }
        }
    """
    now = datetime.now(timezone.utc)
    today_iso = now.strftime("%Y-%m-%dT00:00:00+00:00")
    h24_iso = (now - timedelta(hours=24)).isoformat()
    d7_iso = (now - timedelta(days=7)).isoformat()

    nudge_kind = "agentic.tool_only_nudge_fired"
    return {
        "tool_only_nudge_fired": {
            "today": _count_kind_since(nudge_kind, today_iso),
            "last_24h": _count_kind_since(nudge_kind, h24_iso),
            "last_7d": _count_kind_since(nudge_kind, d7_iso),
            "recent_fires": _recent_kind(nudge_kind, d7_iso, limit=10),
        },
    }
