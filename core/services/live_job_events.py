"""Bounded, process-local live projection of background-job events.

The job registries and their log files remain authoritative.  This module is
only a lossy delivery layer for Desk: producers never wait for subscribers,
reconnects can replay a short tail, and a stale cursor asks the route for a
fresh canonical snapshot.
"""
from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass, replace
from datetime import UTC, datetime
import threading
from typing import Any


_REPLAY_SIZE = 512
_QUEUE_SIZE = 128
_PRESERVED_TYPES = frozenset({"job_started", "job_finished", "source_status"})


def _timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class JobEvent:
    cursor: int
    event_type: str
    job_key: str
    session_id: str
    source: str
    timestamp: str
    payload: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "cursor": self.cursor,
            "type": self.event_type,
            "job_key": self.job_key,
            "session_id": self.session_id,
            "source": self.source,
            "timestamp": self.timestamp,
            "payload": dict(self.payload),
        }


class JobSubscription:
    def __init__(
        self,
        owner: "LiveJobEventHub",
        *,
        session_id: str,
        initial_events: list[JobEvent],
        needs_snapshot: bool,
        queue_size: int,
    ) -> None:
        self._owner = owner
        self.session_id = str(session_id or "")
        self.initial_events = initial_events
        self.needs_snapshot = bool(needs_snapshot)
        self.queue: asyncio.Queue[JobEvent] = asyncio.Queue(maxsize=max(1, queue_size))
        self._closed = False
        self._truncated_pending = False
        try:
            self._loop: asyncio.AbstractEventLoop | None = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = None

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._owner._unsubscribe(self)

    def _deliver(self, event: JobEvent) -> None:
        if self._closed:
            return
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._enqueue, event)
        else:
            self._enqueue(event)

    def _enqueue(self, event: JobEvent) -> None:
        if self._closed:
            return
        if self.queue.full():
            queued: list[JobEvent] = []
            while True:
                try:
                    queued.append(self.queue.get_nowait())
                except asyncio.QueueEmpty:  # normal afslutning på et ikke-blokerende drain
                    break

            drop_at = next(
                (idx for idx, queued_event in enumerate(queued)
                 if queued_event.event_type == "job_output"),
                None,
            )
            if drop_at is not None:
                queued.pop(drop_at)
                self._truncated_pending = True
            elif event.event_type not in _PRESERVED_TYPES:
                # The queue contains lifecycle events. Drop this lossy update,
                # not a start/finish/source-health transition.
                for queued_event in queued:
                    self.queue.put_nowait(queued_event)
                self._truncated_pending = True
                return
            else:
                # A tiny custom queue can contain only lifecycle events. The
                # newest terminal/source fact is more useful than its oldest
                # predecessor, and remains replayable in the hub ring.
                queued.pop(0)

            for queued_event in queued:
                self.queue.put_nowait(queued_event)

        if self._truncated_pending:
            payload = dict(event.payload)
            payload["output_truncated"] = True
            event = replace(event, payload=payload)
            self._truncated_pending = False
        self.queue.put_nowait(event)


class LiveJobEventHub:
    def __init__(self, *, replay_size: int = _REPLAY_SIZE) -> None:
        if replay_size < 1:
            raise ValueError("replay_size must be positive")
        self._events: deque[JobEvent] = deque(maxlen=int(replay_size))
        self._subscribers: set[JobSubscription] = set()
        self._cursor = 0
        self._lock = threading.Lock()

    def publish(
        self,
        event_type: str,
        *,
        job_key: str,
        session_id: str,
        source: str,
        payload: dict[str, Any],
    ) -> JobEvent:
        with self._lock:
            self._cursor += 1
            event = JobEvent(
                cursor=self._cursor,
                event_type=str(event_type),
                job_key=str(job_key),
                session_id=str(session_id or ""),
                source=str(source),
                timestamp=_timestamp(),
                payload=dict(payload or {}),
            )
            self._events.append(event)
            subscribers = tuple(self._subscribers)
        for subscriber in subscribers:
            if not event.session_id or event.session_id == subscriber.session_id:
                subscriber._deliver(event)
        return event

    def subscribe(
        self,
        *,
        session_id: str,
        after: int | None,
        queue_size: int = _QUEUE_SIZE,
    ) -> JobSubscription:
        with self._lock:
            events = list(self._events)
            needs_snapshot = after is None
            initial: list[JobEvent] = []
            if after is not None:
                oldest = events[0].cursor if events else self._cursor + 1
                needs_snapshot = int(after) < oldest - 1
                if not needs_snapshot:
                    initial = [
                        event for event in events
                        if event.cursor > int(after)
                        and (not event.session_id or event.session_id == session_id)
                    ]
            subscription = JobSubscription(
                self,
                session_id=session_id,
                initial_events=initial,
                needs_snapshot=needs_snapshot,
                queue_size=queue_size,
            )
            self._subscribers.add(subscription)
        return subscription

    def _unsubscribe(self, subscription: JobSubscription) -> None:
        with self._lock:
            self._subscribers.discard(subscription)

    def snapshot_cursor(self) -> int:
        with self._lock:
            return self._cursor


_HUB = LiveJobEventHub()


def publish(
    event_type: str,
    *,
    job_key: str,
    session_id: str,
    source: str,
    payload: dict[str, Any],
) -> JobEvent:
    return _HUB.publish(
        event_type,
        job_key=job_key,
        session_id=session_id,
        source=source,
        payload=payload,
    )


def subscribe(
    *, session_id: str, after: int | None, queue_size: int = _QUEUE_SIZE
) -> JobSubscription:
    return _HUB.subscribe(session_id=session_id, after=after, queue_size=queue_size)


def snapshot_cursor() -> int:
    return _HUB.snapshot_cursor()


def reset_for_tests() -> None:
    global _HUB
    _HUB = LiveJobEventHub()
