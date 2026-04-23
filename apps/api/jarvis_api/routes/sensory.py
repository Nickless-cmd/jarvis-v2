"""Sansernes Arkiv HTTP endpoints.

GET  /api/sensory            — list recent sensory memories
GET  /api/sensory/search     — substring search over content/mood_tone
GET  /api/sensory/summary    — compact summary (counts per modality + recent)
GET  /api/sensory/{id}       — single memory
POST /api/sensory            — record a sensory memory (internal use)

Query params on list: modality, limit, offset, since (ISO timestamp).
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from core.services import sensory_archive

router = APIRouter(prefix="/api/sensory", tags=["sensory"])


class SensoryRecordPayload(BaseModel):
    modality: str = Field(..., description="visual | audio | atmosphere | mixed")
    content: str = Field(..., min_length=1)
    mood_tone: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


@router.get("")
def list_memories(
    modality: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    since: str | None = Query(default=None),
) -> dict[str, Any]:
    items = sensory_archive.list_recent(
        modality=modality, limit=limit, offset=offset, since=since
    )
    return {"items": items, "count": len(items)}


@router.get("/search")
def search_memories(
    q: str = Query(..., min_length=1),
    modality: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    items = sensory_archive.search(q, modality=modality, limit=limit)
    return {"items": items, "count": len(items), "query": q}


@router.get("/summary")
def summary() -> dict[str, Any]:
    return sensory_archive.summarize_for_context(limit=5)


@router.get("/{memory_id}")
def get_memory(memory_id: str) -> dict[str, Any]:
    item = sensory_archive.get(memory_id)
    if not item:
        raise HTTPException(status_code=404, detail="sensory memory not found")
    return item


@router.post("")
def record_memory(payload: SensoryRecordPayload) -> dict[str, Any]:
    try:
        record = sensory_archive._record(
            payload.modality,
            payload.content,
            mood_tone=payload.mood_tone,
            metadata=payload.metadata,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return record
