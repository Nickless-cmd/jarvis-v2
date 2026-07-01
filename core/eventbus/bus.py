from __future__ import annotations

import json
import logging
import queue
import sqlite3
import threading
import time
from typing import Any

from core.eventbus.events import Event
from core.runtime.db import connect

logger = logging.getLogger(__name__)

_WRITER_QUEUE_MAXSIZE = 10_000
_FLUSH_POLL_SECS = 0.001
_WRITER_SHUTDOWN_TIMEOUT = 5.0


class EventBus:
    """Thread-safe event bus with async SQLite writes.

    publish() queues the event to a dedicated writer thread for SQLite
    INSERT + causal edges, then notifies subscribers AFTER the write
    commits.  This decouples fast publish-callers (service threads,
    agentic loops) from slow SQLite I/O.

    Thread safety — the writer is a single thread processing a FIFO
    queue, so events are committed in publish order.  Subscriber
    notification runs on the writer thread but is *non-blocking*
    (queue.put_nowait on each subscriber's in-memory queue), so the
    writer is never stalled by slow subscribers.

    flush() is provided for tests that need to read their writes back
    synchronously.
    """

    def __init__(self) -> None:
        self._subscribers: list[queue.Queue[dict[str, Any] | None]] = []
        self._lock = threading.Lock()

        # ---- Async writer machinery ----
        self._writer_queue: queue.Queue[dict[str, Any] | None] = queue.Queue(
            maxsize=_WRITER_QUEUE_MAXSIZE
        )
        self._seq_lock = threading.Lock()
        self._publish_seq: int = 0  # incremented per publish (next seq to hand out)
        self._write_seq: int = 0  # seq of the last committed event

        self._writer_shutdown = threading.Event()
        self._writer_thread = threading.Thread(
            target=self._writer_loop,
            daemon=True,
            name="eventbus-writer",
        )
        self._writer_thread.start()

    # ---- Public API ---------------------------------------------------

    def publish(
        self,
        kind: str,
        payload: dict[str, Any] | None = None,
        *,
        caused_by: int | list[int] | None = None,
        edge_kind: str = "triggered",
    ) -> None:
        """Publish an event.  Returns immediately — the actual write is async."""
        # Resolve parent (EventContext if caller didn't provide explicit).
        if caused_by is None:
            try:
                from core.eventbus.context import get_current_event

                caused_by = get_current_event()
            except Exception:
                caused_by = None

        event = Event.create(kind=kind, payload=payload)
        payload_json = json.dumps(event.payload, ensure_ascii=False)
        created_at = event.ts.isoformat()

        # Serialise all data the writer needs so we don't hold references.
        item: dict[str, Any] = {
            "kind": event.kind,
            "payload": event.payload,
            "payload_json": payload_json,
            "created_at": created_at,
            "caused_by": caused_by,
            "edge_kind": edge_kind,
        }

        with self._seq_lock:
            seq = self._publish_seq
            self._publish_seq += 1
        # seq tracks "the Nth event published" (1-based), not the 0-based index.
        # This way flush() can compare write_seq >= publish_seq directly.
        seq = seq + 1
        item["seq"] = seq

        try:
            self._writer_queue.put_nowait(item)
        except queue.Full:
            logger.error(
                "eventbus-writer queue FULL (limit=%d) — dropping event kind=%s seq=%d",
                _WRITER_QUEUE_MAXSIZE,
                kind,
                seq,
            )
            # Still advance write_seq so flush() doesn't wait forever for
            # an event we'll never process.
            with self._seq_lock:
                self._write_seq = seq

    def flush(self, timeout: float = 10.0) -> None:
        """Block until the writer has committed *all* events published so far.

        Intended for tests.  Production code should not need this.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self._seq_lock:
                if self._write_seq >= self._publish_seq:
                    return
            time.sleep(_FLUSH_POLL_SECS)
        logger.warning(
            "eventbus.flush() timed out after %.1fs — "
            "publish_seq=%d write_seq=%d queue_size=%d",
            timeout,
            self._publish_seq,
            self._write_seq,
            self._writer_queue.qsize(),
        )

    def stop(self) -> None:
        """Graceful shutdown: drain the writer thread."""
        self._writer_shutdown.set()
        self._writer_queue.put(None)  # poison pill wakes writer
        self._writer_thread.join(timeout=_WRITER_SHUTDOWN_TIMEOUT)
        if self._writer_thread.is_alive():
            logger.warning("eventbus-writer did not exit within timeout")

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

    # ---- Writer thread -------------------------------------------------

    def _writer_loop(self) -> None:
        """Dedicated thread: pull items from queue, write to SQLite, notify."""
        while not self._writer_shutdown.is_set():
            try:
                item = self._writer_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if item is None:  # poison pill
                break

            try:
                self._write_event(item)
            except sqlite3.OperationalError as exc:
                # Rygraden: DB-lås trods busy_timeout (fx lang checkpoint) → ét retry efter
                # kort pause før vi opgiver. Undgår at tabe events på kortvarig kontention.
                time.sleep(0.2)
                try:
                    self._write_event(item)
                except Exception:
                    logger.warning(
                        "eventbus-writer: dropped event efter retry kind=%s (%s)",
                        item.get("kind", "?"), exc,
                    )
            except Exception:
                logger.exception(
                    "eventbus-writer: failed to write event kind=%s",
                    item.get("kind", "?"),
                )
            finally:
                # Always advance the sequence so flush() doesn't deadlock.
                seq = item.get("seq", -1)
                with self._seq_lock:
                    if seq >= self._write_seq:
                        self._write_seq = seq

    def _write_event(self, item: dict[str, Any]) -> None:
        kind = item["kind"]
        payload_json = item["payload_json"]
        created_at = item["created_at"]
        caused_by = item.get("caused_by")
        edge_kind = item.get("edge_kind", "triggered")

        with connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO events (kind, payload_json, created_at)
                VALUES (?, ?, ?)
                """,
                (kind, payload_json, created_at),
            )
            event_id = int(cursor.lastrowid)

            # Write causal edges. Best-effort — never let edge-write
            # break event publication.
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

        # Notify subscribers *after* the write is committed so their
        # on-read queries see the event.  put_nowait is non-blocking.
        serialized = self._serialize_event(
            event_id=event_id,
            event_kind=kind,
            event_payload=item["payload"],
            created_at=created_at,
        )
        self._notify_subscribers(serialized)

    # ---- Internal helpers ---------------------------------------------

    def _notify_subscribers(self, item: dict[str, Any]) -> None:
        with self._lock:
            subscribers = list(self._subscribers)
        for subscriber in subscribers:
            try:
                subscriber.put_nowait(item)
            except Exception:
                pass  # a slow subscriber should not stall the bus

    def _serialize_event(
        self,
        *,
        event_id: int,
        event_kind: str,
        event_payload: dict[str, Any],
        created_at: str,
    ) -> dict[str, Any]:
        payload_json = json.dumps(event_payload, ensure_ascii=False)
        family = event_kind.split(".", 1)[0]
        return {
            "id": event_id,
            "kind": event_kind,
            "family": family,
            "payload": event_payload,
            "payload_json": payload_json,
            "created_at": created_at,
        }

    def _deserialize_row(
        self,
        *,
        event_id: int,
        kind: str,
        payload_json: str,
        created_at: str,
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
        return self._serialize_event(
            event_id=event_id,
            event_kind=event.kind,
            event_payload=event.payload,
            created_at=created_at,
        )


event_bus = EventBus()
