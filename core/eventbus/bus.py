from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from core.runtime.db import connect


class EventBus:
    def publish(self, kind: str, payload: dict[str, Any] | None = None) -> None:
        payload = payload or {}
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO events (kind, payload_json, created_at)
                VALUES (?, ?, ?)
                """,
                (
                    kind,
                    json.dumps(payload, ensure_ascii=False),
                    datetime.now(UTC).isoformat(),
                ),
            )
            conn.commit()

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


event_bus = EventBus()
