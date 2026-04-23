"""Sensory archive tools — record and recall sensory experiences.

Two tools for Jarvis's visible lane:
- record_sensory_memory: write a visual/audio/atmosphere/mixed impression
- recall_sensory_memories: list or search existing impressions

Thin wrappers over core.services.sensory_archive.
"""
from __future__ import annotations

from typing import Any

from core.services import sensory_archive

_VALID_MODALITIES = ("visual", "audio", "atmosphere", "mixed")


def _exec_record_sensory_memory(args: dict[str, Any]) -> dict[str, Any]:
    modality = str(args.get("modality") or "").strip().lower()
    content = str(args.get("content") or "").strip()
    mood_tone = args.get("mood_tone")
    metadata = args.get("metadata") or {}
    if modality not in _VALID_MODALITIES:
        return {
            "status": "error",
            "error": f"modality must be one of {list(_VALID_MODALITIES)}",
        }
    if not content:
        return {"status": "error", "error": "content is required"}
    if not isinstance(metadata, dict):
        return {"status": "error", "error": "metadata must be an object"}
    try:
        record = sensory_archive._record(
            modality,
            content,
            mood_tone=(str(mood_tone).strip() if mood_tone else None),
            metadata=metadata,
        )
    except ValueError as exc:
        return {"status": "error", "error": str(exc)}
    return {"status": "ok", "memory": record}


def _exec_recall_sensory_memories(args: dict[str, Any]) -> dict[str, Any]:
    query = str(args.get("query") or "").strip()
    modality = args.get("modality")
    if modality:
        modality = str(modality).strip().lower()
        if modality not in _VALID_MODALITIES:
            return {
                "status": "error",
                "error": f"modality must be one of {list(_VALID_MODALITIES)}",
            }
    try:
        limit = int(args.get("limit") or 20)
    except (TypeError, ValueError):
        limit = 20
    limit = max(1, min(100, limit))

    if query:
        items = sensory_archive.search(query, modality=modality, limit=limit)
    else:
        items = sensory_archive.list_recent(modality=modality, limit=limit)
    return {
        "status": "ok",
        "count": len(items),
        "items": items,
        "total": sensory_archive.count(modality=modality),
    }


SENSORY_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "record_sensory_memory",
            "description": (
                "Write a sensory impression to Sansernes Arkiv — your persistent "
                "archive of visual, audio, atmospheric, and mixed experiences. "
                "Use this when you see, hear, or sense something worth keeping. "
                "Content should capture atmosphere and meaning, not just a flat "
                "inventory. Mood tone is a short mood label (e.g. 'roligt', "
                "'anspændt', 'varmt'). Metadata is free-form (source daemon, "
                "location, luminosity, db level, etc.)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "modality": {
                        "type": "string",
                        "enum": list(_VALID_MODALITIES),
                        "description": "Sensory modality.",
                    },
                    "content": {
                        "type": "string",
                        "description": "Rich description of the experience.",
                    },
                    "mood_tone": {
                        "type": "string",
                        "description": "Short mood/tone label, optional.",
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Free-form JSON metadata, optional.",
                    },
                },
                "required": ["modality", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recall_sensory_memories",
            "description": (
                "Recall sensory impressions from Sansernes Arkiv. With no query, "
                "lists the most recent. With a query, does substring search over "
                "content and mood tone. Optionally filter by modality."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Optional substring to search for.",
                    },
                    "modality": {
                        "type": "string",
                        "enum": list(_VALID_MODALITIES),
                        "description": "Optional modality filter.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results (1-100, default 20).",
                    },
                },
            },
        },
    },
]
