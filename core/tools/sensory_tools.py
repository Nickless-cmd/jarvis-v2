"""Sensory archive tools — record and recall sensory experiences.

Two tools for Jarvis's visible lane:
- record_sensory_memory: write a visual/audio/atmosphere/mixed impression
- recall_sensory_memories: list or search existing impressions

Thin wrappers over core.services.sensory_archive.
"""
from __future__ import annotations

from typing import Any

from core.services import sensory_archive
from core.services import scoped_recall_policy

_VALID_MODALITIES = ("visual", "audio", "atmosphere", "mixed")


def _exec_record_sensory_memory(args: dict[str, Any]) -> dict[str, Any]:
    try:
        user_id = scoped_recall_policy.require_private_scope()
    except scoped_recall_policy.MissingRecallScope as exc:  # Private writes require a bound user.
        return {"status": "error", "error": str(exc)}
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

    # `source` er en top-level parameter (schema + beskrivelse), men
    # normaliseringen i sensory_source læser `metadata['source']`. Fold den
    # ind her, så et top-level source ikke tabes. Målt 17/10-2026: nattens
    # tre natrutine-poster fik 'ukendt', fordi parameteren ikke fandtes i
    # schemaet og handleren derfor aldrig så den.
    source = args.get("source")
    if source:
        metadata = {**metadata, "source": source}

    # Egress-fri Central-observation (§24.4): Jarvis fanger et SANSE-indtryk. Kun
    # modalitet-label + længde — ALDRIG selve indholdet/sansningen. Self-safe.
    try:
        from core.services.central_private_observe import record_private
        record_private(
            "cognition", "sensory_record",
            value=float(len(content)),
            meta={"modality": str(modality), "chars": len(content),
                  "has_mood": bool(mood_tone)},
            reason="sensory intake",
        )
    except Exception:  # Optional scalar observation must not block the private write.
        pass

    # Queue the write for async processing — returns immediately.
    # The memory_write_queue daemon processes the write in background.
    from core.services.memory_write_queue import enqueue_write
    queue_id = enqueue_write(
        "sensory",
        {
            "user_id": user_id,
            "modality": modality,
            "content": content,
            "mood_tone": str(mood_tone).strip() if mood_tone else None,
            "metadata": metadata,
        },
    )
    if queue_id:
        return {
            "status": "ok",
            "queued": True,
            "queue_id": queue_id,
            "text": f"Sensory memory ({modality}) queued for async write.",
        }
    # Fallback: direct write if queue is unavailable
    try:
        record = sensory_archive._record(
            modality,
            content,
            mood_tone=(str(mood_tone).strip() if mood_tone else None),
            metadata=metadata,
        )
    except ValueError as exc:  # Validation errors are returned without a partial write.
        return {"status": "error", "error": str(exc)}
    return {"status": "ok", "memory": record}


def _exec_recall_sensory_memories(args: dict[str, Any]) -> dict[str, Any]:
    if not scoped_recall_policy.recall_enabled():
        return scoped_recall_policy.disabled_result("sensory_recall")
    try:
        scoped_recall_policy.require_private_scope()
    except scoped_recall_policy.MissingRecallScope as exc:  # Private reads fail closed.
        return {"status": "error", "error": str(exc), "items": [], "count": 0}
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
                "'anspændt', 'varmt'). Metadata is free-form ("
                "location, luminosity, db level, etc.). `source` is normalised "
                "to a fixed set of producers — pass the tool or routine that "
                "produced the impression (e.g. 'look_around', 'mic_listen', "
                "'natrutine', 'dybdesession'); anything unrecognised is kept "
                "as 'ukendt' with the raw name preserved in 'source_raw'."
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
                    "source": {
                        "type": "string",
                        "description": (
                            "Producer of the impression — e.g. 'look_around', "
                            "'mic_listen', 'natrutine', 'dybdesession'. "
                            "Normalised to a canonical set; unknown names "
                            "become 'ukendt' with the raw value in 'source_raw'."
                        ),
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
