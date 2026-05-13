"""Curiosity-observations weekly consolidation.

Phase 1 of curiosity-budget stored observations but never synthesized them.
This module runs a weekly LLM-pass that identifies patterns across the
last 7 days of observations and produces a short consolidation note that
feeds into next meta-learning memo + awareness injection.

Triggered by cadence-scheduler (ProducerSpec). Cheap-lane LLM call.

Added 2026-05-13.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from core.runtime.db import connect

logger = logging.getLogger(__name__)

_SCHEMA_INITIALIZED = False


def ensure_schema() -> None:
    global _SCHEMA_INITIALIZED
    if _SCHEMA_INITIALIZED:
        return
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS curiosity_consolidations (
              consolidation_id TEXT PRIMARY KEY,
              ts TEXT NOT NULL,
              period_start TEXT NOT NULL,
              period_end TEXT NOT NULL,
              n_observations INTEGER NOT NULL,
              summary TEXT NOT NULL,
              model_used TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_curi_cons_ts
              ON curiosity_consolidations(ts);
            """
        )
        conn.commit()
    _SCHEMA_INITIALIZED = True


def _fetch_observations(since: datetime, until: datetime) -> list[dict[str, Any]]:
    try:
        with connect() as conn:
            rows = conn.execute(
                "SELECT id, ts, action, observation_text, follow_up_hint "
                "FROM curiosity_observations WHERE ts >= ? AND ts <= ? "
                "ORDER BY ts",
                (since.isoformat(), until.isoformat()),
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception as exc:
        logger.debug("curiosity_consolidation: fetch failed: %s", exc)
        return []


def _build_prompt(observations: list[dict[str, Any]]) -> str:
    bullets = []
    for o in observations[:30]:
        bullets.append(
            f"- [{o.get('action') or '?'}] {str(o.get('observation_text') or '')[:160]}"
        )
    return (
        "Læs disse curiosity-observationer fra de seneste 7 dage og "
        "identificér 1-2 tilbagevendende mønstre eller temaer.\n"
        "\n"
        "Output: 80-150 ord prosa, dansk, deskriptiv ton. Ikke punktliste. "
        "Returnér kun selve teksten, ingen overskrifter.\n"
        "\n"
        + "\n".join(bullets)
    )


def run_consolidation(*, now: datetime | None = None) -> dict[str, Any]:
    """Build a consolidation note from last 7d observations."""
    ensure_schema()
    now = now or datetime.now(UTC)
    since = now - timedelta(days=7)
    obs = _fetch_observations(since=since, until=now)
    if len(obs) < 3:
        return {"status": "skipped", "reason": "too-few-observations", "n": len(obs)}

    try:
        from core.services.cheap_provider_runtime import execute_public_safe_cheap_lane
        result = execute_public_safe_cheap_lane(message=_build_prompt(obs))
    except Exception as exc:
        return {"status": "error", "reason": f"cheap-lane: {exc}"}

    summary = str(result.get("text") or "").strip()
    if len(summary) < 40:
        return {"status": "error", "reason": "summary-too-short", "raw": summary[:120]}
    summary = summary[:1200]  # bound stored text

    cid = f"curi-cons-{uuid4().hex[:12]}"
    with connect() as conn:
        conn.execute(
            "INSERT INTO curiosity_consolidations (consolidation_id, ts, "
            "period_start, period_end, n_observations, summary, model_used) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (cid, now.isoformat(), since.isoformat(), now.isoformat(),
             len(obs), summary, str(result.get("model") or "")),
        )
        conn.commit()

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("cognitive_state.curiosity_consolidated", {
            "consolidation_id": cid, "n_observations": len(obs),
            "summary_length": len(summary),
        })
    except Exception:
        pass

    return {"status": "ok", "consolidation_id": cid, "n_observations": len(obs),
            "summary": summary}


def latest_consolidation_for_awareness() -> str:
    """Awareness section showing the most recent consolidation (≤7d old)."""
    ensure_schema()
    try:
        with connect() as conn:
            row = conn.execute(
                "SELECT ts, summary FROM curiosity_consolidations "
                "ORDER BY ts DESC LIMIT 1"
            ).fetchone()
    except Exception:
        return ""
    if not row:
        return ""
    try:
        ts = datetime.fromisoformat(row["ts"])
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        if datetime.now(UTC) - ts > timedelta(days=8):
            return ""  # stale, skip
    except (ValueError, TypeError):
        return ""
    return f"Curiosity consolidation (seneste uge):\n{row['summary']}"
