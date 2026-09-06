from __future__ import annotations

import json
import logging
import sqlite3
import threading
from datetime import UTC, datetime, timedelta
from typing import Callable

from core.runtime.db_core import connect

logger = logging.getLogger(__name__)

_POLL_SECONDS = 5.0
_worker_lock = threading.Lock()
_worker_started = False


def _now() -> str:
    return datetime.now(UTC).isoformat()


def ensure_approval_outbox_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS approval_notification_outbox (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id TEXT NOT NULL UNIQUE,
            user_id TEXT NOT NULL,
            envelope_json TEXT NOT NULL,
            state TEXT NOT NULL DEFAULT 'pending',
            attempts INTEGER NOT NULL DEFAULT 0,
            next_attempt_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            delivered_at TEXT,
            last_error TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_approval_notification_outbox_due
        ON approval_notification_outbox(state, next_attempt_at, id)
        """
    )


def enqueue_approval_notification(
    conn: sqlite3.Connection,
    *,
    request_id: str,
    user_id: str,
    envelope: dict[str, object],
) -> None:
    ensure_approval_outbox_table(conn)
    now = _now()
    conn.execute(
        """
        INSERT OR IGNORE INTO approval_notification_outbox (
            request_id, user_id, envelope_json, state, attempts,
            next_attempt_at, created_at
        ) VALUES (?, ?, ?, 'pending', 0, ?, ?)
        """,
        (request_id, user_id, json.dumps(envelope, sort_keys=True), now, now),
    )


def pending_approval_notifications(limit: int = 20) -> list[dict[str, object]]:
    now = _now()
    with connect() as conn:
        ensure_approval_outbox_table(conn)
        rows = conn.execute(
            """
            SELECT request_id, user_id, envelope_json, attempts, next_attempt_at
            FROM approval_notification_outbox
            WHERE state = 'pending' AND next_attempt_at <= ?
            ORDER BY id ASC LIMIT ?
            """,
            (now, max(int(limit), 1)),
        ).fetchall()
    return [
        {
            "request_id": row["request_id"],
            "user_id": row["user_id"],
            "envelope": json.loads(str(row["envelope_json"])),
            "attempts": int(row["attempts"]),
            "next_attempt_at": row["next_attempt_at"],
        }
        for row in rows
    ]


def make_approval_notification_due(request_id: str) -> None:
    with connect() as conn:
        ensure_approval_outbox_table(conn)
        conn.execute(
            """
            UPDATE approval_notification_outbox
            SET next_attempt_at = ? WHERE request_id = ? AND state = 'pending'
            """,
            ("1970-01-01T00:00:00+00:00", request_id),
        )
        conn.commit()


def dispatch_pending_approval_notifications(
    *,
    limit: int = 20,
    deliver: Callable[[str, dict[str, object]], bool] | None = None,
) -> dict[str, int]:
    if deliver is None:
        from core.services.push_dispatcher import on_approval_requested

        deliver = on_approval_requested
    delivered = 0
    failed = 0
    for item in pending_approval_notifications(limit=limit):
        request_id = str(item["request_id"])
        attempts = int(item["attempts"])
        error = "delivery returned false"
        try:
            ok = bool(deliver(str(item["user_id"]), dict(item["envelope"])))
        except Exception as exc:
            ok = False
            error = str(exc)
        with connect() as conn:
            ensure_approval_outbox_table(conn)
            if ok:
                conn.execute(
                    """
                    UPDATE approval_notification_outbox
                    SET state = 'delivered', delivered_at = ?, last_error = NULL
                    WHERE request_id = ? AND state = 'pending'
                    """,
                    (_now(), request_id),
                )
                delivered += 1
            else:
                retry_at = datetime.now(UTC) + timedelta(
                    seconds=min(300, 2 ** min(attempts + 1, 8))
                )
                conn.execute(
                    """
                    UPDATE approval_notification_outbox
                    SET attempts = attempts + 1, next_attempt_at = ?, last_error = ?
                    WHERE request_id = ? AND state = 'pending'
                    """,
                    (retry_at.isoformat(), error[:500], request_id),
                )
                failed += 1
            conn.commit()
    return {"delivered": delivered, "failed": failed}


def _worker() -> None:
    while True:
        try:
            dispatch_pending_approval_notifications()
        except Exception as exc:
            logger.warning("approval outbox dispatch failed: %s", exc)
        threading.Event().wait(_POLL_SECONDS)


def start_approval_outbox_dispatcher() -> bool:
    global _worker_started
    with _worker_lock:
        if _worker_started:
            return False
        _worker_started = True
        threading.Thread(
            target=_worker,
            name="approval-outbox-dispatcher",
            daemon=True,
        ).start()
    return True
