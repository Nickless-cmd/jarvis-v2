"""Conversation-continuity topics, deliberately separate from world truth."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from core.runtime.db_world_self_truth import (
    select_conversation_topics,
    upsert_conversation_topic,
)


def record_conversation_topic(
    *,
    canonical_key: str,
    title: str,
    summary: str = "",
    source_kind: str = "",
    session_id: str = "",
    run_id: str = "",
) -> dict[str, object]:
    normalized_key = str(canonical_key or "").strip()
    normalized_title = " ".join(str(title or "").split()).strip()
    if not normalized_key:
        raise ValueError("canonical_key is required")
    if not normalized_title:
        raise ValueError("title is required")
    now = datetime.now(UTC).isoformat()
    return upsert_conversation_topic(
        topic_id=f"topic-{uuid4().hex}",
        canonical_key=normalized_key,
        title=normalized_title,
        summary=" ".join(str(summary or "").split()).strip(),
        source_kind=str(source_kind or "").strip(),
        session_id=str(session_id or "").strip(),
        run_id=str(run_id or "").strip(),
        created_at=now,
        updated_at=now,
    )


def list_conversation_topics(*, limit: int = 20) -> list[dict[str, object]]:
    return select_conversation_topics(limit=limit)

