"""Semantic indexer — auto-embedding of new memory records.

Two cooperating workers:
- Event subscriber: embeds sensory_memories the instant they land
  (low volume, real-time relevance for visible recall).
- Background sweeper: every 5 minutes runs backfill_all() to catch
  new private_brain_records and any other registered sources.
  Backfill skips rows whose content_hash is already indexed, so
  repeated runs are cheap.
"""
from __future__ import annotations

import logging
import queue
import threading
from typing import Any

from core.eventbus.bus import event_bus

logger = logging.getLogger(__name__)

_SUBSCRIBER_THREAD: threading.Thread | None = None
_SUBSCRIBER_STOP = threading.Event()
_SUBSCRIBER_QUEUE: queue.Queue[dict[str, Any] | None] | None = None

_SWEEPER_THREAD: threading.Thread | None = None
_SWEEPER_STOP = threading.Event()
_SWEEPER_INTERVAL_SECONDS = 300  # 5 minutes

_SENSORY_EVENT = "memory.sensory.recorded"
_PRIVATE_BRAIN_EVENT = "memory.private_brain.recorded"


def start_semantic_indexer() -> None:
    global _SUBSCRIBER_THREAD, _SUBSCRIBER_QUEUE, _SWEEPER_THREAD
    if _SUBSCRIBER_THREAD and _SUBSCRIBER_THREAD.is_alive():
        return
    _SUBSCRIBER_STOP.clear()
    _SWEEPER_STOP.clear()
    subscriber = event_bus.subscribe()
    _SUBSCRIBER_QUEUE = subscriber
    thread = threading.Thread(
        target=_subscriber_loop,
        kwargs={"subscriber": subscriber},
        name="jarvis-semantic-indexer",
        daemon=True,
    )
    thread.start()
    _SUBSCRIBER_THREAD = thread

    sweeper = threading.Thread(
        target=_sweeper_loop,
        name="jarvis-semantic-sweeper",
        daemon=True,
    )
    sweeper.start()
    _SWEEPER_THREAD = sweeper

    logger.info("semantic_indexer: started (event + sweeper)")


def stop_semantic_indexer() -> None:
    global _SUBSCRIBER_THREAD, _SUBSCRIBER_QUEUE, _SWEEPER_THREAD
    _SUBSCRIBER_STOP.set()
    _SWEEPER_STOP.set()
    subscriber = _SUBSCRIBER_QUEUE
    if subscriber is not None:
        event_bus.unsubscribe(subscriber)
    thread = _SUBSCRIBER_THREAD
    if thread and thread.is_alive():
        thread.join(timeout=1.0)
    sweeper = _SWEEPER_THREAD
    if sweeper and sweeper.is_alive():
        sweeper.join(timeout=1.0)
    _SUBSCRIBER_THREAD = None
    _SUBSCRIBER_QUEUE = None
    _SWEEPER_THREAD = None
    logger.info("semantic_indexer: stopped")


def _sweeper_loop() -> None:
    """Every N minutes, run backfill_all to catch new rows without events."""
    from core.services.semantic_memory import backfill_all

    while not _SWEEPER_STOP.is_set():
        if _SWEEPER_STOP.wait(timeout=_SWEEPER_INTERVAL_SECONDS):
            return
        try:
            result = backfill_all(max_per_table=200)
            if result.get("total_indexed"):
                logger.info(
                    "semantic_indexer: sweep indexed %s new rows",
                    result.get("total_indexed"),
                )
        except Exception as exc:
            logger.debug("semantic_indexer: sweep failed: %s", exc)


def _subscriber_loop(*, subscriber: queue.Queue[dict[str, Any] | None]) -> None:
    while not _SUBSCRIBER_STOP.is_set():
        try:
            item = subscriber.get(timeout=0.5)
        except queue.Empty:
            continue
        if item is None:
            break
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "")
        payload = item.get("payload") or {}
        try:
            if kind == _SENSORY_EVENT:
                _handle_sensory(payload)
            elif kind == _PRIVATE_BRAIN_EVENT:
                _handle_private_brain(payload)
        except Exception as exc:
            logger.debug("semantic_indexer: handler error: %s", exc)


def _handle_sensory(payload: dict[str, Any]) -> None:
    sid = str(payload.get("id") or "").strip()
    if not sid:
        return
    from core.runtime.db_sensory import get_sensory_memory
    from core.services.semantic_memory import index_memory

    record = get_sensory_memory(sid)
    if not record:
        return
    content = str(record.get("content") or "")
    modality = str(record.get("modality") or "mixed")
    index_memory(
        source_table="sensory_memories",
        source_id=sid,
        content=content,
        modality=modality,
    )


def _handle_private_brain(payload: dict[str, Any]) -> None:
    rid = str(payload.get("record_id") or "").strip()
    if not rid:
        return
    from core.runtime.db import get_private_brain_record
    from core.services.semantic_memory import index_memory

    record = get_private_brain_record(rid)
    if not record:
        return
    summary = str(record.get("summary") or "").strip()
    detail = str(record.get("detail") or "").strip()
    text = summary
    if detail and detail != summary:
        text = f"{summary}\n{detail}" if summary else detail
    modality = str(
        record.get("record_type") or record.get("layer") or "inner"
    )
    index_memory(
        source_table="private_brain_records",
        source_id=rid,
        content=text,
        modality=modality,
    )
