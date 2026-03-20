from __future__ import annotations

import json
import queue
import threading
from datetime import UTC, datetime
from typing import Any

from core.runtime.db import connect


class EventBus:
    def __init__(self) -> None:
        self._subscribers: list[queue.Queue[dict[str, Any] | None]] = []
        self._lock = threading.Lock()

    def publish(self, kind: str, payload: dict[str, Any] | None = None) -> None:
        payload = payload or {}
        created_at = datetime.now(UTC).isoformat()
        with connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO events (kind, payload_json, created_at)
                VALUES (?, ?, ?)
                """,
                (
                    kind,
                    json.dumps(payload, ensure_ascii=False),
                    created_at,
                ),
            )
            conn.commit()
            event_id = int(cursor.lastrowid)

        item = {
            "id": event_id,
            "kind": kind,
            "payload_json": json.dumps(payload, ensure_ascii=False),
            "created_at": created_at,
        }
        self._notify_subscribers(item)

    def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT id, kind, payload_json, created_at
                FROM events
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "kind": row["kind"],
                "payload_json": row["payload_json"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def subscribe(self) -> queue.Queue[dict[str, Any] | None]:
        subscriber: queue.Queue[dict[str, Any] | None] = queue.Queue()
        with self._lock:
            self._subscribers.append(subscriber)
        return subscriber

    def unsubscribe(self, subscriber: queue.Queue[dict[str, Any] | None]) -> None:
        with self._lock:
            if subscriber in self._subscribers:
                self._subscribers.remove(subscriber)
        subscriber.put_nowait(None)

    def _notify_subscribers(self, item: dict[str, Any]) -> None:
        with self._lock:
            subscribers = list(self._subscribers)
        for subscriber in subscribers:
            subscriber.put_nowait(item)


event_bus = EventBus()
