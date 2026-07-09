"""Paste-store endpoints: eksternalisér store bruger-pastes + lazy resolve.

- `POST /paste`  {text} → {paste_id, reference}  (composer eksternaliserer store pastes)
- `GET  /paste/{id}`     → {id, text, line_count, created_at}  (lazy resolve til historik-render)

Fil-baseret via `core.services.paste_store` (hash-baseret idempotent id).
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.services.paste_store import (
    build_paste_reference,
    get_paste,
    save_paste,
)

router = APIRouter(prefix="/paste", tags=["paste"])


class PasteSaveRequest(BaseModel):
    text: str


@router.post("")
async def save_paste_endpoint(request: PasteSaveRequest) -> dict:
    """Gem en paste og returnér id + kompakt reference-streng."""
    text = str(request.text or "")
    if not text.strip():
        raise HTTPException(status_code=400, detail="text must not be empty")
    paste_id = save_paste(text)
    stored = get_paste(paste_id) or {}
    line_count = int(stored.get("line_count") or 0)
    return {
        "paste_id": paste_id,
        "reference": build_paste_reference(paste_id, line_count=line_count),
        "line_count": line_count,
    }


@router.get("/{paste_id}")
async def get_paste_endpoint(paste_id: str) -> dict:
    """Slå fuld paste-tekst op (lazy resolve). 404 på ukendt id."""
    stored = get_paste(paste_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="Paste not found")
    return {
        "id": stored.get("id"),
        "text": stored.get("text"),
        "line_count": stored.get("line_count"),
        "created_at": stored.get("created_at"),
    }
