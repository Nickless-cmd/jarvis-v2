"""Semantic recall tools — Jarvis-facing recall across all memory surfaces.

recall_memories: embed the query, cosine-match against every indexed
memory (sensory + private brain), return top hits with source record
excerpts so Jarvis can decide what to do with them.
"""
from __future__ import annotations

from typing import Any

from core.services import semantic_memory

_VALID_MODALITIES = (
    "visual",
    "audio",
    "atmosphere",
    "mixed",
    "inner",
    "inner-voice",
    "ambient-sound",
    "visual-memory",
    "chronicle",
    "reflection",
    "dream",
    "shadow-finding",
)


def _excerpt_for(record: dict[str, Any] | None, source_table: str) -> str:
    if not record:
        return ""
    if source_table == "sensory_memories":
        return str(record.get("content") or "")[:400]
    if source_table == "private_brain_records":
        summary = str(record.get("summary") or "").strip()
        detail = str(record.get("detail") or "").strip()
        if summary and detail and summary != detail:
            return f"{summary} — {detail}"[:400]
        return (summary or detail)[:400]
    return ""


def _timestamp_for(record: dict[str, Any] | None, source_table: str) -> str:
    if not record:
        return ""
    if source_table == "sensory_memories":
        return str(record.get("timestamp") or "")
    if source_table == "private_brain_records":
        return str(record.get("created_at") or "")
    return ""


def _exec_recall_memories(args: dict[str, Any]) -> dict[str, Any]:
    query = str(args.get("query") or "").strip()
    if not query:
        return {"status": "error", "error": "query is required"}

    raw_modalities = args.get("modalities")
    modalities: list[str] | None = None
    if isinstance(raw_modalities, str):
        modalities = [m.strip() for m in raw_modalities.split(",") if m.strip()]
    elif isinstance(raw_modalities, list):
        modalities = [str(m).strip() for m in raw_modalities if str(m).strip()]
    if modalities is not None and not modalities:
        modalities = None

    raw_sources = args.get("source_tables")
    source_tables: list[str] | None = None
    if isinstance(raw_sources, str):
        source_tables = [m.strip() for m in raw_sources.split(",") if m.strip()]
    elif isinstance(raw_sources, list):
        source_tables = [str(m).strip() for m in raw_sources if str(m).strip()]
    if source_tables is not None and not source_tables:
        source_tables = None

    try:
        limit = int(args.get("limit") or 10)
    except (TypeError, ValueError):
        limit = 10
    limit = max(1, min(50, limit))

    try:
        min_score = float(args.get("min_score") or 0.35)
    except (TypeError, ValueError):
        min_score = 0.35
    min_score = max(0.0, min(1.0, min_score))

    hits = semantic_memory.search(
        query,
        modalities=modalities,
        source_tables=source_tables,
        limit=limit,
        min_score=min_score,
    )

    items = []
    for h in hits:
        items.append(
            {
                "score": h.get("score"),
                "source_table": h.get("source_table"),
                "source_id": h.get("source_id"),
                "modality": h.get("modality"),
                "indexed_at": h.get("indexed_at"),
                "timestamp": _timestamp_for(h.get("record"), str(h.get("source_table") or "")),
                "excerpt": _excerpt_for(h.get("record"), str(h.get("source_table") or "")),
            }
        )

    return {
        "status": "ok",
        "query": query,
        "count": len(items),
        "items": items,
        "stats": semantic_memory.get_stats(),
    }


RECALL_MEMORY_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "recall_memories",
            "description": (
                "Semantic search across Jarvis's full memory — sensory "
                "archive (visual/audio/atmosphere/mixed) and private brain "
                "(inner-voice, reflections, chronicle, dreams, shadow, "
                "ambient-sound). Returns the most semantically similar "
                "records with excerpts, ranked by cosine similarity. Use "
                "this to find past experiences, thoughts, or observations "
                "that relate to a current question — not substring match, "
                "but meaning-match."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What you're looking for (natural language).",
                    },
                    "modalities": {
                        "type": "array",
                        "items": {"type": "string", "enum": list(_VALID_MODALITIES)},
                        "description": "Optional modality filter.",
                    },
                    "source_tables": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["sensory_memories", "private_brain_records"],
                        },
                        "description": "Optional source table filter.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results (1-50, default 10).",
                    },
                    "min_score": {
                        "type": "number",
                        "description": "Minimum cosine score 0-1 (default 0.35).",
                    },
                },
                "required": ["query"],
            },
        },
    }
]
