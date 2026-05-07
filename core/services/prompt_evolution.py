"""Prompt evolution — versioning + rollback safety net for workspace prompts.

Porteret fra jarvis-ai/agent/ecosystem/prompt_evolution.py (2026-05-07),
men reduceret scope til det der faktisk mangler i v2:

Original gør 3 ting:
1. Snapshot workspace prompt files før mutation
2. Auto-mutate via apply_runtime_prompt_update (LLM-drevet)
3. Score outcome, auto-rollback ved negativ score

V2-version (denne fil) gør #1 + #3 manuel-version af. #2 (auto-mutate)
springes over fordi:
- v2 har ikke en LLM-drevet runtime prompt updater
- Bjørns kerne-behov per 7. maj samtale: SIKKERHEDSNET — "hvis ændring
  gjorde tingene værre, vend tilbage". Det er rollback der giver værdi,
  ikke mutationen selv.

API:
- snapshot_workspace_file(filename, content, reason) — gem version
- list_prompt_history(filename, limit) — recent versions
- rollback_to_version(filename, version_id) — restore version
- recommend_rollback_after_change(filename, hours) — score telemetry,
  fortæl om en recent ændring ser dårligt ud (gør IKKE selv rollback —
  det er bevidst beslutning, ikke automatik)
"""
from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import connect

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _ensure_table() -> None:
    """Create workspace_prompt_versions table if missing. Idempotent."""
    with connect() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS workspace_prompt_versions (
                version_id TEXT PRIMARY KEY,
                workspace_id TEXT NOT NULL DEFAULT 'default',
                filename TEXT NOT NULL,
                content TEXT NOT NULL,
                content_sha256 TEXT NOT NULL,
                reason TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                created_by TEXT NOT NULL DEFAULT 'system'
            )
            """
        )
        c.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_wpv_filename_created
            ON workspace_prompt_versions(filename, created_at DESC)
            """
        )


def snapshot_workspace_file(
    *,
    filename: str,
    content: str,
    reason: str = "",
    workspace_id: str = "default",
    created_by: str = "system",
) -> dict[str, Any] | None:
    """Persist a snapshot of a workspace file.

    Idempotent on identical content — if the most recent version for this
    filename has the same sha256, no new row is created (caller still gets
    that existing version dict back). Use ``reason`` to explain WHY this
    snapshot was taken (e.g. "before identity_mutation", "auto-snapshot
    pre-edit").
    """
    _ensure_table()
    sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
    try:
        with connect() as c:
            existing = c.execute(
                """
                SELECT version_id, content_sha256, created_at
                FROM workspace_prompt_versions
                WHERE filename = ?
                ORDER BY created_at DESC LIMIT 1
                """,
                (filename,),
            ).fetchone()
            if existing and str(existing["content_sha256"]) == sha:
                return {
                    "version_id": str(existing["version_id"]),
                    "filename": filename,
                    "content_sha256": sha,
                    "created_at": str(existing["created_at"]),
                    "reason": "no-op-identical-content",
                    "deduped": True,
                }
            version_id = f"wpv-{uuid4().hex[:14]}"
            now = _now_iso()
            c.execute(
                """
                INSERT INTO workspace_prompt_versions
                (version_id, workspace_id, filename, content, content_sha256,
                 reason, created_at, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (version_id, workspace_id, filename, content, sha,
                 reason, now, created_by),
            )
        try:
            event_bus.publish(
                "runtime.workspace_prompt_snapshot",
                {
                    "version_id": version_id,
                    "filename": filename,
                    "reason": reason,
                    "created_by": created_by,
                },
            )
        except Exception:
            pass
        return {
            "version_id": version_id,
            "filename": filename,
            "content_sha256": sha,
            "created_at": now,
            "reason": reason,
            "deduped": False,
        }
    except Exception as exc:
        logger.warning("prompt_evolution: snapshot failed for %s: %s", filename, exc)
        return None


def list_prompt_history(
    *, filename: str, limit: int = 20
) -> list[dict[str, Any]]:
    """Return recent versions of a file, newest first. Excludes content
    body to keep payloads light — call get_version() to fetch full text.
    """
    _ensure_table()
    try:
        with connect() as c:
            rows = c.execute(
                """
                SELECT version_id, filename, content_sha256, reason,
                       created_at, created_by
                FROM workspace_prompt_versions
                WHERE filename = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (filename, limit),
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception as exc:
        logger.warning("prompt_evolution: list_history failed: %s", exc)
        return []


def get_version(*, version_id: str) -> dict[str, Any] | None:
    """Fetch a specific version including full content."""
    _ensure_table()
    try:
        with connect() as c:
            row = c.execute(
                """
                SELECT version_id, workspace_id, filename, content,
                       content_sha256, reason, created_at, created_by
                FROM workspace_prompt_versions WHERE version_id = ?
                """,
                (version_id,),
            ).fetchone()
        return dict(row) if row else None
    except Exception as exc:
        logger.warning("prompt_evolution: get_version failed: %s", exc)
        return None


def rollback_to_version(
    *,
    workspace_dir: Path,
    filename: str,
    version_id: str,
    snapshot_current_first: bool = True,
) -> dict[str, Any]:
    """Restore a workspace file to a specific historical version.

    Default behavior: snapshots the CURRENT content first (so rollback
    itself is undoable), then writes the historical content. Set
    ``snapshot_current_first=False`` only if caller has already snapshotted.

    Returns dict with status. Never raises — failures get logged + reported.
    """
    target = get_version(version_id=version_id)
    if not target:
        return {"status": "error", "reason": f"version not found: {version_id}"}
    if str(target.get("filename")) != filename:
        return {
            "status": "error",
            "reason": f"version filename mismatch: {target.get('filename')} vs {filename}",
        }

    file_path = Path(workspace_dir) / filename
    try:
        # Snapshot current state before overwriting (safety: can rollback the rollback)
        if snapshot_current_first and file_path.exists():
            current_content = file_path.read_text(encoding="utf-8")
            snapshot_workspace_file(
                filename=filename,
                content=current_content,
                reason=f"pre-rollback-to-{version_id}",
                created_by="rollback",
            )
        file_path.write_text(str(target.get("content") or ""), encoding="utf-8")
    except Exception as exc:
        return {"status": "error", "reason": f"write failed: {exc}"}

    try:
        event_bus.publish(
            "runtime.workspace_prompt_rollback",
            {
                "version_id": version_id,
                "filename": filename,
                "rolled_back_to_created_at": str(target.get("created_at") or ""),
            },
        )
    except Exception:
        pass
    return {
        "status": "ok",
        "version_id": version_id,
        "filename": filename,
        "rolled_back_to_created_at": str(target.get("created_at") or ""),
    }


def recommend_rollback_after_change(
    *,
    filename: str,
    hours: int = 6,
) -> dict[str, Any]:
    """Score recent telemetry to assess whether the most recent change to
    ``filename`` correlates with degraded behavior. Read-only — DOES NOT
    rollback. Returns recommendation that caller (Bjørn or a daemon) can
    act on consciously.

    Heuristic v1: compare counts of these event families before vs after
    the most recent snapshot:
    - tool.error (errors after the change → bad signal)
    - heartbeat.conflict_resolved (conflicts → bad signal)
    - decision.deduped (commitment churn → mild bad signal)

    More events of these classes after the change than before = recommend
    rollback. This is a v1 heuristic — not the LLM-scored mutation evaluator
    in jarvis-ai's original. Adequate for the safety-net use case.
    """
    history = list_prompt_history(filename=filename, limit=2)
    if len(history) < 1:
        return {"recommendation": "no-data", "reason": "no_history_for_file"}
    last_change = history[0]
    last_change_at = str(last_change.get("created_at") or "").strip()
    if not last_change_at:
        return {"recommendation": "no-data", "reason": "no_change_timestamp"}

    try:
        change_dt = datetime.fromisoformat(last_change_at.replace("Z", "+00:00"))
    except Exception:
        return {"recommendation": "no-data", "reason": "bad_timestamp"}

    window_start = change_dt - timedelta(hours=hours)
    window_end = change_dt + timedelta(hours=hours)

    bad_families = ("tool.error", "heartbeat.conflict_resolved", "decision.deduped")

    def _count(start: str, end: str) -> int:
        try:
            with connect() as c:
                # eventbus events table is conventionally `eventbus_events`
                row = c.execute(
                    """
                    SELECT COUNT(*) AS n FROM eventbus_events
                    WHERE created_at >= ? AND created_at < ?
                      AND event_type IN ({})
                    """.format(",".join("?" * len(bad_families))),
                    (start, end, *bad_families),
                ).fetchone()
            return int(row["n"]) if row else 0
        except Exception as exc:
            logger.debug("prompt_evolution: count fail: %s", exc)
            return 0

    before = _count(window_start.isoformat(), last_change_at)
    after = _count(last_change_at, window_end.isoformat())

    if after >= before * 2 and after >= 3:
        recommendation = "rollback-suggested"
        reason = f"bad-event-count {before} → {after} after change"
    elif after > before and after >= 2:
        recommendation = "watch"
        reason = f"slight-rise {before} → {after}"
    else:
        recommendation = "keep"
        reason = f"no-degradation {before} → {after}"

    return {
        "recommendation": recommendation,
        "reason": reason,
        "filename": filename,
        "version_id": last_change.get("version_id"),
        "change_at": last_change_at,
        "bad_events_before": before,
        "bad_events_after": after,
        "window_hours": hours,
    }
