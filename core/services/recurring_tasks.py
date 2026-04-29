"""Recurring tasks service — lets Jarvis schedule repeating reminders/actions.

A background poller (60s interval) checks for due recurring tasks, fires them
via session notification + initiative queue (same delivery as scheduled_tasks),
then advances next_fire_at by the task's interval_minutes.
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.runtime import db as runtime_db

logger = logging.getLogger(__name__)

_POLL_INTERVAL_SECONDS = 60
_poller_thread: threading.Thread | None = None
_poller_stop = threading.Event()


# ── DB helpers (self-contained, no db.py modification needed) ────────────────

def _ensure_table() -> None:
    with runtime_db.connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS recurring_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL UNIQUE,
                focus TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'jarvis-tool',
                status TEXT NOT NULL DEFAULT 'active',
                interval_minutes INTEGER NOT NULL,
                next_fire_at TEXT NOT NULL,
                last_fired_at TEXT NOT NULL DEFAULT '',
                fire_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_recurring_tasks_status_next
            ON recurring_tasks(status, next_fire_at)
            """
        )
        conn.commit()


def _row_to_dict(row) -> dict:
    return {
        "task_id": row["task_id"],
        "focus": row["focus"],
        "source": row["source"],
        "status": row["status"],
        "interval_minutes": row["interval_minutes"],
        "next_fire_at": row["next_fire_at"],
        "last_fired_at": row["last_fired_at"],
        "fire_count": row["fire_count"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _create(*, task_id: str, focus: str, source: str, interval_minutes: int, next_fire_at: str, now: str) -> None:
    with runtime_db.connect() as conn:
        conn.execute(
            """
            INSERT INTO recurring_tasks
              (task_id, focus, source, status, interval_minutes, next_fire_at, created_at, updated_at)
            VALUES (?, ?, ?, 'active', ?, ?, ?, ?)
            """,
            (task_id, focus, source, interval_minutes, next_fire_at, now, now),
        )
        conn.commit()


def _get_due(now_iso: str) -> list[dict]:
    with runtime_db.connect() as conn:
        rows = conn.execute(
            "SELECT * FROM recurring_tasks WHERE status = 'active' AND next_fire_at <= ? ORDER BY next_fire_at ASC LIMIT 20",
            (now_iso,),
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def _advance(task_id: str, interval_minutes: int, now: datetime) -> None:
    next_fire = (now + timedelta(minutes=interval_minutes)).isoformat()
    now_iso = now.isoformat()
    with runtime_db.connect() as conn:
        conn.execute(
            """
            UPDATE recurring_tasks
            SET next_fire_at = ?, last_fired_at = ?, fire_count = fire_count + 1, updated_at = ?
            WHERE task_id = ?
            """,
            (next_fire, now_iso, now_iso, task_id),
        )
        conn.commit()


def _cancel(task_id: str, now_iso: str) -> bool:
    with runtime_db.connect() as conn:
        cur = conn.execute(
            "UPDATE recurring_tasks SET status = 'cancelled', updated_at = ? WHERE task_id = ? AND status != 'cancelled'",
            (now_iso, task_id),
        )
        conn.commit()
        return cur.rowcount > 0


def _list(limit: int = 50) -> list[dict]:
    with runtime_db.connect() as conn:
        rows = conn.execute(
            "SELECT * FROM recurring_tasks ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def _get_one(task_id: str) -> dict | None:
    with runtime_db.connect() as conn:
        row = conn.execute("SELECT * FROM recurring_tasks WHERE task_id = ?", (task_id,)).fetchone()
    return _row_to_dict(row) if row else None


# ── Public service API ────────────────────────────────────────────────────────

def create_recurring_task(
    *,
    focus: str,
    interval_minutes: int,
    source: str = "jarvis-tool",
    delay_minutes: int = 0,
) -> dict:
    """Schedule a recurring task. Returns task info dict."""
    _ensure_table()
    now = datetime.now(UTC)
    first_fire = now + timedelta(minutes=max(delay_minutes, interval_minutes))
    task_id = f"rec-{uuid4().hex[:10]}"
    focus = focus[:300].strip() or "Recurring reminder"
    _create(
        task_id=task_id,
        focus=focus,
        source=source,
        interval_minutes=interval_minutes,
        next_fire_at=first_fire.isoformat(),
        now=now.isoformat(),
    )
    logger.info("recurring_tasks: created %s every %dm focus=%r", task_id, interval_minutes, focus[:60])
    return {
        "task_id": task_id,
        "focus": focus,
        "interval_minutes": interval_minutes,
        "next_fire_at": first_fire.isoformat(),
        "status": "active",
    }


def cancel_recurring_task(task_id: str) -> bool:
    _ensure_table()
    ok = _cancel(task_id, datetime.now(UTC).isoformat())
    if ok:
        logger.info("recurring_tasks: cancelled %s", task_id)
    return ok


def list_recurring_tasks() -> list[dict]:
    _ensure_table()
    return _list()


def get_recurring_tasks_state() -> dict:
    """Summary for observability / Mission Control."""
    _ensure_table()
    tasks = _list()
    active = [t for t in tasks if t["status"] == "active"]
    cancelled = [t for t in tasks if t["status"] == "cancelled"]
    return {
        "active": active,
        "cancelled_count": len(cancelled),
        "total": len(tasks),
    }


# ── Poller ────────────────────────────────────────────────────────────────────

def _fire_due() -> None:
    _ensure_table()
    now = datetime.now(UTC)
    due = _get_due(now.isoformat())
    if not due:
        return

    # Recurring tasks should EXECUTE the focus (autonomously do the work)
    # rather than just send themselves as a reminder. Without this, a task
    # like "Send morgenbriefing til Bjørn kl 07:00 via Discord: vejr, nyheder,
    # noget inspirerende" would just deliver the focus text back to the user
    # as a notification — useless. Triggering an autonomous run lets Jarvis
    # use his tools (discord_channel.send, web_search etc.) to actually carry
    # out the task. The focus becomes the user-message of an autonomous run.
    from core.services.visible_runs import start_autonomous_run

    for task in due:
        task_id = str(task["task_id"])
        focus = str(task["focus"])
        interval_minutes = int(task["interval_minutes"])
        try:
            # Use autonomous run as the PRIMARY execution path.
            # Push to initiative queue only as a fallback signal — but do NOT
            # let both paths produce a user-visible message independently.
            # Dedup: if start_autonomous_run succeeds, initiative is redundant
            # for user-facing delivery, so we skip it to avoid double messages.
            start_autonomous_run(message=focus, session_id=None)
            _advance(task_id, interval_minutes, now)
            logger.info(
                "recurring_tasks: fired %s as autonomous run (every %dm)",
                task_id,
                interval_minutes,
            )
        except Exception as exc:
            logger.error("recurring_tasks: error firing %s: %s", task_id, exc)


def _poller_loop() -> None:
    while not _poller_stop.is_set():
        try:
            _fire_due()
        except Exception as exc:
            logger.error("recurring_tasks: poller error: %s", exc)
        _poller_stop.wait(_POLL_INTERVAL_SECONDS)


def start_recurring_tasks_service() -> None:
    global _poller_thread
    _poller_stop.clear()
    t = threading.Thread(target=_poller_loop, daemon=True, name="recurring-tasks-poller")
    t.start()
    _poller_thread = t
    logger.info("recurring_tasks: service started (poll interval %ds)", _POLL_INTERVAL_SECONDS)


def stop_recurring_tasks_service() -> None:
    _poller_stop.set()
    logger.info("recurring_tasks: service stopped")
