"""MC observability for tool_router."""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter

from core.runtime.db import connect
from core.runtime.settings import RuntimeSettings

router = APIRouter(prefix="/mc", tags=["mc-tool-router"])


def _bucket_count(values: list[float], n_buckets: int = 10) -> list[int]:
    buckets = [0] * n_buckets
    for v in values:
        if v is None:
            continue
        idx = min(n_buckets - 1, max(0, int(float(v) * n_buckets)))
        buckets[idx] += 1
    return buckets


@router.get("/tool-router-state")
def get_state() -> dict:
    s = RuntimeSettings()
    now = datetime.now(timezone.utc)
    today_iso = now.strftime("%Y-%m-%dT00:00:00+00:00")
    d7_iso = (now - timedelta(days=7)).isoformat()

    with connect() as c:
        decisions_today = c.execute(
            "SELECT COUNT(*) FROM tool_router_decisions WHERE created_at >= ?", (today_iso,),
        ).fetchone()[0]
        decisions_7d = c.execute(
            "SELECT COUNT(*) FROM tool_router_decisions WHERE created_at >= ?", (d7_iso,),
        ).fetchone()[0]
        fallback_7d = c.execute(
            "SELECT COUNT(*) FROM tool_router_decisions "
            "WHERE fallback_used = 1 AND created_at >= ?", (d7_iso,),
        ).fetchone()[0]
        load_more_7d = c.execute(
            "SELECT COUNT(*) FROM tool_router_load_more WHERE created_at >= ?", (d7_iso,),
        ).fetchone()[0]
        avg_saved = c.execute(
            "SELECT AVG(tokens_saved_estimate) FROM tool_router_decisions "
            "WHERE created_at >= ?", (d7_iso,),
        ).fetchone()[0] or 0
        avg_elapsed = c.execute(
            "SELECT AVG(elapsed_ms) FROM tool_router_decisions "
            "WHERE created_at >= ?", (d7_iso,),
        ).fetchone()[0] or 0
        confidence_rows = c.execute(
            "SELECT confidence FROM tool_router_decisions "
            "WHERE created_at >= ?", (d7_iso,),
        ).fetchall()
        recent_rows = c.execute(
            "SELECT created_at, user_message_preview, confidence, threshold, "
            "fallback_used, fallback_reason, "
            "json_array_length(selected_names_json) AS selected_count, elapsed_ms "
            "FROM tool_router_decisions ORDER BY id DESC LIMIT 20"
        ).fetchall()
        miss_rows = c.execute(
            "SELECT resolved_names_json FROM tool_router_load_more "
            "WHERE created_at >= ?", (d7_iso,),
        ).fetchall()

    miss_counts: dict[str, int] = {}
    for r in miss_rows:
        try:
            for n in json.loads(r[0] or "[]"):
                miss_counts[n] = miss_counts.get(n, 0) + 1
        except Exception:
            pass
    top_missed = sorted(
        ({"name": n, "count": cnt} for n, cnt in miss_counts.items()),
        key=lambda r: r["count"], reverse=True,
    )[:10]

    fallback_rate = (float(fallback_7d) / float(decisions_7d)) if decisions_7d else 0.0
    load_more_rate = (float(load_more_7d) / float(decisions_7d)) if decisions_7d else 0.0

    return {
        "enabled": s.tool_router_enabled,
        "config": {
            "threshold": s.tool_router_threshold,
            "always_core_size": s.tool_router_always_core_size,
            "k_embeddings": s.tool_router_k_embeddings,
            "embedding_model": s.tool_router_embedding_model,
        },
        "totals": {
            "decisions_today": decisions_today,
            "decisions_7d": decisions_7d,
            "fallback_rate_7d": fallback_rate,
            "load_more_rate_7d": load_more_rate,
            "avg_tokens_saved_7d": int(avg_saved),
            "avg_elapsed_ms": float(avg_elapsed),
        },
        "top_missed_tools_7d": top_missed,
        "confidence_histogram": _bucket_count([float(r[0]) for r in confidence_rows if r[0] is not None]),
        "recent_decisions": [
            {
                "at": r[0],
                "preview": r[1],
                "confidence": r[2],
                "threshold": r[3],
                "fallback_used": bool(r[4]),
                "fallback_reason": r[5],
                "selected_count": r[6],
                "elapsed_ms": r[7],
            }
            for r in recent_rows
        ],
    }
