from __future__ import annotations

import json
import queue
import threading
from typing import Any

from core.eventbus.events import Event
from core.runtime.db import connect


class EventBus:
    def __init__(self) -> None:
        self._subscribers: list[queue.Queue[dict[str, Any] | None]] = []
        self._lock = threading.Lock()

    def publish(
        self,
        kind: str,
        payload: dict[str, Any] | None = None,
        *,
        caused_by: int | list[int] | None = None,
        edge_kind: str = "triggered",
    ) -> None:
        # Auto-pickup parent from EventContext if caller didn't specify.
        # Explicit caused_by always wins over context.
        if caused_by is None:
            try:
                from core.eventbus.context import get_current_event
                caused_by = get_current_event()
            except Exception:
                caused_by = None

        event = Event.create(kind=kind, payload=payload)
        payload_json = json.dumps(event.payload, ensure_ascii=False)
        created_at = event.ts.isoformat()
        with connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO events (kind, payload_json, created_at)
                VALUES (?, ?, ?)
                """,
                (
                    event.kind,
                    payload_json,
                    created_at,
                ),
            )
            event_id = int(cursor.lastrowid)
            # Write causal edges if parent(s) given. Best-effort —
            # never let edge-write break event publication.
            if caused_by is not None:
                parents = caused_by if isinstance(caused_by, list) else [caused_by]
                for pid in parents:
                    try:
                        conn.execute(
                            """
                            INSERT OR IGNORE INTO causal_edges
                            (child_event_id, parent_event_id, edge_kind,
                             confidence, source, created_at, reasoning)
                            VALUES (?, ?, ?, 1.0, 'explicit', ?, '')
                            """,
                            (event_id, int(pid), edge_kind, created_at),
                        )
                    except Exception:
                        pass
            conn.commit()

        item = self._serialize_event(event_id=event_id, event=event)
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
            self._deserialize_row(
                event_id=int(row["id"]),
                kind=row["kind"],
                payload_json=row["payload_json"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def recent_by_family(self, family: str, *, limit: int = 50) -> list[dict[str, Any]]:
        """Return the latest events whose kind belongs to a given family.

        Family is the prefix before the first dot in `kind` (see Event.from_record).
        Use this when a caller would otherwise pull recent(limit=N) and filter
        client-side — that pattern misses entire families when high-volume kinds
        like circadian.energy_changed dominate the recent window.
        """
        family_clean = str(family or "").strip()
        if not family_clean:
            return []
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT id, kind, payload_json, created_at
                FROM events
                WHERE kind LIKE ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (f"{family_clean}.%", max(int(limit), 1)),
            ).fetchall()
        return [
            self._deserialize_row(
                event_id=int(row["id"]),
                kind=row["kind"],
                payload_json=row["payload_json"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def recent_since_id(self, after_id: int, *, limit: int = 100) -> list[dict[str, Any]]:
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT id, kind, payload_json, created_at
                FROM events
                WHERE id > ?
                ORDER BY id ASC
                LIMIT ?
                """,
                (max(int(after_id), 0), max(int(limit), 1)),
            ).fetchall()
        return [
            self._deserialize_row(
                event_id=int(row["id"]),
                kind=row["kind"],
                payload_json=row["payload_json"],
                created_at=row["created_at"],
            )
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

    def _serialize_event(self, *, event_id: int, event: Event) -> dict[str, Any]:
        payload_json = json.dumps(event.payload, ensure_ascii=False)
        return {
            "id": event_id,
            "kind": event.kind,
            "family": event.family,
            "payload": event.payload,
            "payload_json": payload_json,
            "created_at": event.ts.isoformat(),
        }

    def _deserialize_row(
        self, *, event_id: int, kind: str, payload_json: str, created_at: str
    ) -> dict[str, Any]:
        payload = json.loads(payload_json)
        try:
            event = Event.from_record(
                kind=kind,
                payload=payload,
                created_at=created_at,
            )
        except ValueError:
            return {
                "id": event_id,
                "kind": kind,
                "family": "unknown",
                "payload": payload,
                "payload_json": payload_json,
                "created_at": created_at,
            }
        return self._serialize_event(event_id=event_id, event=event)


event_bus = EventBus()
