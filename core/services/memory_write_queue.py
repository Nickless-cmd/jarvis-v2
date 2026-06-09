"""Memory Write Queue — async write queue for sensory/brain memories.

Three write types are deferred to a SQLite-backed queue so tool calls
return immediately and the actual I/O happens in a background daemon:

  - **sensory**: insert into sensory_memories table + publish eventbus event
  - **brain**: write brain entry file + SQLite index
  - **memory_sidecar**: mood capture + graph ingestion after MEMORY.md write

The daemon (`tick_memory_write_queue_daemon`) processes pending items every
2 minutes in batches of 10, with retries and error isolation.

Semantic embedding is already handled asynchronously by `semantic_indexer.py`
(event subscriber + 5-min sweeper), so we don't duplicate that here.
"""
from __future__ import annotations

import json
import logging
import traceback
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_CADENCE_SECONDS = 120          # daemon tick interval
_BATCH_SIZE = 10                # max items per tick
_MAX_RETRIES = 3                # max retry attempts per item
_SENSORY_MAX_RETRIES = 3
_BRAIN_MAX_RETRIES = 3
_SIDECAR_MAX_RETRIES = 5        # sidecar is best-effort, more retries

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_last_tick_at: datetime | None = None
_last_result: dict[str, Any] = {}

_VALID_TYPES = frozenset({"sensory", "brain", "memory_sidecar"})

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _ensure_table(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS memory_write_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            queue_id TEXT NOT NULL UNIQUE,
            queue_type TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            priority INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'pending',
            retry_count INTEGER NOT NULL DEFAULT 0,
            error TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            processed_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_memory_write_queue_pending
        ON memory_write_queue(status, priority DESC, id ASC)
        """
    )


def enqueue_write(
    queue_type: str,
    payload: dict[str, Any],
    priority: int = 0,
) -> str:
    """Enqueue a memory write for async processing.

    Args:
        queue_type: One of 'sensory', 'brain', 'memory_sidecar'.
        payload: Type-specific payload dict.
        priority: Higher = processed first (default 0).

    Returns:
        queue_id string. Empty string on error.
    """
    if queue_type not in _VALID_TYPES:
        logger.warning("memory_write_queue: invalid type %r", queue_type)
        return ""

    queue_id = f"mwq-{uuid4().hex[:12]}"
    now = datetime.now(UTC).isoformat()

    try:
        from core.runtime.db import connect
        with connect() as conn:
            _ensure_table(conn)
            conn.execute(
                """
                INSERT INTO memory_write_queue
                    (queue_id, queue_type, payload_json, priority, status, created_at)
                VALUES (?, ?, ?, ?, 'pending', ?)
                """,
                (queue_id, queue_type, json.dumps(payload, ensure_ascii=False),
                 priority, now),
            )
    except Exception as exc:
        logger.error("memory_write_queue: enqueue failed: %s", exc)
        return ""

    return queue_id


def process_queue(batch_size: int = _BATCH_SIZE) -> dict[str, Any]:
    """Process pending write queue items. Called by the daemon tick.

    Returns a dict with counts: processed, succeeded, failed, remaining.
    """
    from core.runtime.db import connect

    processed = 0
    succeeded = 0
    failed = 0
    errors: list[str] = []

    try:
        with connect() as conn:
            _ensure_table(conn)
            rows = conn.execute(
                """
                SELECT id, queue_id, queue_type, payload_json, retry_count
                FROM memory_write_queue
                WHERE status = 'pending'
                ORDER BY priority DESC, id ASC
                LIMIT ?
                """,
                (batch_size,),
            ).fetchall()

            for row in rows:
                item_id = row["id"]
                queue_id = row["queue_id"]
                queue_type = row["queue_type"]
                retry_count = row["retry_count"]
                payload = json.loads(row["payload_json"])

                # Mark as processing
                conn.execute(
                    "UPDATE memory_write_queue SET status = 'processing' WHERE id = ?",
                    (item_id,),
                )
                conn.commit()

                # Process
                ok, error_msg = _process_item(queue_type, payload, retry_count)
                processed += 1

                if ok:
                    conn.execute(
                        "UPDATE memory_write_queue SET status = 'done', processed_at = ? WHERE id = ?",
                        (datetime.now(UTC).isoformat(), item_id),
                    )
                    succeeded += 1
                else:
                    new_retry = retry_count + 1
                    max_r = _max_retries_for(queue_type)
                    if new_retry >= max_r:
                        conn.execute(
                            """UPDATE memory_write_queue
                               SET status = 'failed', retry_count = ?, error = ?
                               WHERE id = ?""",
                            (new_retry, error_msg[:500], item_id),
                        )
                        failed += 1
                    else:
                        conn.execute(
                            """UPDATE memory_write_queue
                               SET status = 'pending', retry_count = ?, error = ?
                               WHERE id = ?""",
                            (new_retry, error_msg[:500], item_id),
                        )
                    errors.append(f"{queue_type}/{queue_id[:12]}: {error_msg[:100]}")

                conn.commit()

        # Check remaining
        remaining = 0
        try:
            with connect() as conn:
                _ensure_table(conn)
                remaining = conn.execute(
                    "SELECT COUNT(*) AS cnt FROM memory_write_queue WHERE status = 'pending'"
                ).fetchone()["cnt"]
        except Exception:
            pass

        result = {
            "processed": processed,
            "succeeded": succeeded,
            "failed": failed,
            "remaining": remaining,
            "errors": errors[:5] if errors else [],
        }
        _last_result = result
        return result

    except Exception as exc:
        logger.error("memory_write_queue: process_queue failed: %s", exc)
        return {"processed": processed, "succeeded": succeeded,
                "failed": failed, "error": str(exc)}


def queue_size() -> dict[str, int]:
    """Return counts by status."""
    from core.runtime.db import connect
    try:
        with connect() as conn:
            _ensure_table(conn)
            rows = conn.execute(
                """SELECT status, COUNT(*) AS cnt
                   FROM memory_write_queue GROUP BY status"""
            ).fetchall()
        counts = {row["status"]: row["cnt"] for row in rows}
        return {
            "pending": counts.get("pending", 0),
            "processing": counts.get("processing", 0),
            "done": counts.get("done", 0),
            "failed": counts.get("failed", 0),
            "total": sum(counts.values()),
        }
    except Exception:
        return {"pending": 0, "processing": 0, "done": 0, "failed": 0, "total": 0}


def build_memory_write_queue_surface() -> dict[str, object]:
    """Mission Control surface."""
    counts = queue_size()
    size_str = ", ".join(f"{k}:{v}" for k, v in counts.items())
    return {
        "active": True,
        "cadence_seconds": _CADENCE_SECONDS,
        "batch_size": _BATCH_SIZE,
        **counts,
        "last_tick_result": _last_result if _last_result else None,
        "summary": (
            f"Queue: {size_str}"
            if counts.get("total", 0) > 0
            else "Queue: empty"
        ),
    }


# ---------------------------------------------------------------------------
# Daemon tick function (registered in daemon_manager)
# ---------------------------------------------------------------------------


def tick_memory_write_queue_daemon(now: datetime | None = None) -> dict:
    """Daemon tick: process pending writes every 120s.

    Registered in daemon_manager._REGISTRY as 'memory_write_queue'.
    """
    global _last_tick_at, _last_result

    now = now or datetime.now(UTC)

    # Cadence gate
    if _last_tick_at is not None:
        if (now - _last_tick_at) < timedelta(seconds=_CADENCE_SECONDS):
            return {"processed": False, "reason": "cadence"}

    result = process_queue(batch_size=_BATCH_SIZE)
    _last_tick_at = now
    _last_result = result

    # Publish event if items were processed
    if result.get("processed", 0) > 0:
        try:
            from core.eventbus.bus import event_bus
            event_bus.publish("memory.write_queue.processed", {
                "processed": result["processed"],
                "succeeded": result["succeeded"],
                "failed": result["failed"],
                "remaining": result.get("remaining", 0),
                "timestamp": now.isoformat(),
            })
        except Exception:
            pass

    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _max_retries_for(queue_type: str) -> int:
    return {
        "sensory": _SENSORY_MAX_RETRIES,
        "brain": _BRAIN_MAX_RETRIES,
        "memory_sidecar": _SIDECAR_MAX_RETRIES,
    }.get(queue_type, _MAX_RETRIES)


def _process_item(
    queue_type: str,
    payload: dict[str, Any],
    retry_count: int,
) -> tuple[bool, str]:
    """Execute one write. Returns (ok, error_message)."""
    try:
        if queue_type == "sensory":
            return _process_sensory(payload, retry_count)
        elif queue_type == "brain":
            return _process_brain(payload, retry_count)
        elif queue_type == "memory_sidecar":
            return _process_sidecar(payload, retry_count)
        else:
            return False, f"unknown type: {queue_type}"
    except Exception as exc:
        tb = traceback.format_exc()
        logger.warning("memory_write_queue: %s item failed: %s\n%s",
                       queue_type, exc, tb)
        return False, str(exc)


def _process_sensory(payload: dict[str, Any], retry_count: int) -> tuple[bool, str]:
    """Process a sensory memory write.

    Payload: {modality, content, mood_tone?, metadata?}
    """
    from core.services.sensory_archive import _record

    modality = str(payload.get("modality") or "mixed")
    content = str(payload.get("content") or "")
    mood_tone = payload.get("mood_tone")
    metadata = payload.get("metadata") or {}

    if not content:
        return False, "empty content"

    _record(modality, content, mood_tone=mood_tone, metadata=metadata)
    return True, ""


def _process_brain(payload: dict[str, Any], retry_count: int) -> tuple[bool, str]:
    """Process a brain entry write.

    Payload: {kind, title, content, visibility, domain, session_id, turn_id,
              related?, tags?, source_url?, source_chronicle?, importance?}
    """
    from core.services.jarvis_brain import write_entry

    kind = str(payload.get("kind") or "observation")
    title = str(payload.get("title") or "")
    content = str(payload.get("content") or "")
    visibility = str(payload.get("visibility") or "personal")
    domain = str(payload.get("domain") or "general")
    related = payload.get("related") or []
    tags = payload.get("tags") or []
    source_url = payload.get("source_url")
    source_chronicle = payload.get("source_chronicle")
    importance = payload.get("importance")

    if not title or not content:
        return False, "empty title or content"

    write_entry(
        kind=kind, title=title, content=content,
        visibility=visibility, domain=domain,
        trigger="spontaneous",
        related=related, tags=tags,
        source_url=source_url, source_chronicle=source_chronicle,
        importance=importance,
    )
    return True, ""


def _process_sidecar(payload: dict[str, Any], retry_count: int) -> tuple[bool, str]:
    """Process a MEMORY.md sidecar: mood capture + graph ingestion.

    Payload: {heading, action, content}
    The MEMORY.md file write itself already happened synchronously —
    this is just the optional post-processing.

    Both are best-effort — failures are tolerable.
    """
    heading = str(payload.get("heading") or "")
    action = str(payload.get("action") or "updated")
    content = str(payload.get("content") or "")

    # Mood capture
    if heading:
        try:
            from core.services.memory_emotional_context import capture_mood_for_heading
            capture_mood_for_heading(heading, source=f"memory_upsert_section:{action}")
        except Exception as exc:
            logger.debug("memory_write_queue: mood capture failed: %s", exc)

    # Graph ingestion
    if content:
        try:
            from core.services.memory_graph import ingest_text
            ingest_text(content, evidence_label=f"memory.md::{heading[:80]}")
        except Exception as exc:
            logger.debug("memory_write_queue: graph ingestion failed: %s", exc)

    return True, ""


# ---------------------------------------------------------------------------
# Retry/recovery helper
# ---------------------------------------------------------------------------


def retry_failed(limit: int = 50) -> int:
    """Reset failed items back to pending for retry.

    Returns number of items reset.
    """
    from core.runtime.db import connect
    try:
        with connect() as conn:
            _ensure_table(conn)
            conn.execute(
                """UPDATE memory_write_queue
                   SET status = 'pending', error = '',
                       retry_count = 0
                   WHERE status = 'failed'
                   LIMIT ?""",
                (limit,),
            )
            affected = conn.total_changes
            conn.commit()
        return affected
    except Exception:
        return 0


def clean_old_done(hours: int = 24) -> int:
    """Delete 'done' items older than N hours.

    Returns number of deleted rows.
    """
    from core.runtime.db import connect
    cutoff = (datetime.now(UTC) - timedelta(hours=hours)).isoformat()
    try:
        with connect() as conn:
            _ensure_table(conn)
            conn.execute(
                "DELETE FROM memory_write_queue WHERE status = 'done' AND created_at < ?",
                (cutoff,),
            )
            affected = conn.total_changes
            conn.commit()
        return affected
    except Exception:
        return 0
