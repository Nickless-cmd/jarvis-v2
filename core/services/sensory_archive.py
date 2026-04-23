"""Sansernes Arkiv — service layer for sensory memories.

Thin wrapper over core.runtime.db_sensory. Publishes events on writes so
downstream daemons (inner_voice, reflection) can react to new sensory
experiences without polling.
"""
from __future__ import annotations

import logging
from typing import Any

from core.eventbus.bus import event_bus
from core.runtime.db_sensory import (
    count_sensory_memories,
    get_sensory_memory,
    insert_sensory_memory,
    list_sensory_memories,
    search_sensory_memories,
)

logger = logging.getLogger(__name__)

__all__ = [
    "record_visual",
    "record_audio",
    "record_atmosphere",
    "record_mixed",
    "list_recent",
    "search",
    "get",
    "count",
    "summarize_for_context",
]


def _record(
    modality: str,
    content: str,
    *,
    mood_tone: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not content or not content.strip():
        raise ValueError("sensory memory content must not be empty")
    record = insert_sensory_memory(
        modality=modality,
        content=content.strip(),
        mood_tone=(mood_tone or None),
        metadata=metadata or {},
    )
    try:
        event_bus.publish(
            "memory.sensory.recorded",
            {
                "id": record["id"],
                "modality": modality,
                "mood_tone": mood_tone,
                "timestamp": record["timestamp"],
            },
        )
    except Exception as exc:
        logger.debug("sensory_archive: event publish failed: %s", exc)
    return record


def record_visual(
    content: str,
    *,
    mood_tone: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _record("visual", content, mood_tone=mood_tone, metadata=metadata)


def record_audio(
    content: str,
    *,
    mood_tone: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _record("audio", content, mood_tone=mood_tone, metadata=metadata)


def record_atmosphere(
    content: str,
    *,
    mood_tone: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _record("atmosphere", content, mood_tone=mood_tone, metadata=metadata)


def record_mixed(
    content: str,
    *,
    mood_tone: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _record("mixed", content, mood_tone=mood_tone, metadata=metadata)


def list_recent(
    *,
    modality: str | None = None,
    limit: int = 50,
    offset: int = 0,
    since: str | None = None,
) -> list[dict[str, Any]]:
    return list_sensory_memories(
        modality=modality, limit=limit, offset=offset, since=since
    )


def search(
    query: str,
    *,
    modality: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    return search_sensory_memories(query=query, modality=modality, limit=limit)


def get(memory_id: str) -> dict[str, Any] | None:
    return get_sensory_memory(memory_id)


def count(*, modality: str | None = None) -> int:
    return count_sensory_memories(modality=modality)


def summarize_for_context(limit: int = 5) -> dict[str, Any]:
    """Return a compact summary usable as surface/context injection."""
    recent = list_recent(limit=limit)
    total = count()
    by_modality = {
        m: count(modality=m)
        for m in ("visual", "audio", "atmosphere", "mixed")
    }
    return {
        "total": total,
        "by_modality": by_modality,
        "recent": [
            {
                "timestamp": r["timestamp"],
                "modality": r["modality"],
                "content": (r["content"] or "")[:160],
                "mood_tone": r.get("mood_tone"),
            }
            for r in recent
        ],
    }
