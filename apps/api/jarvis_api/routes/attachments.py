"""Attachment upload and serve endpoints.

Files are saved to ~/.jarvis-v2/uploads/{session_id}/{uuid}_{filename}.
Metadata is kept in an in-memory registry (_registry) — lost on server restart,
which is acceptable for session-scoped attachments.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from apps.api.jarvis_api.services.chat_sessions import get_chat_session

router = APIRouter(prefix="/attachments", tags=["attachments"])

_MAX_FILE_BYTES = 200 * 1024 * 1024  # 200 MB
_MAX_IMAGES_PER_SESSION = 25
_UPLOAD_DIR = Path.home() / ".jarvis-v2" / "uploads"

_registry: dict[str, "AttachmentMeta"] = {}


@dataclass
class AttachmentMeta:
    id: str
    session_id: str
    filename: str
    mime_type: str
    size_bytes: int
    server_path: str


def get_attachment(attachment_id: str) -> AttachmentMeta | None:
    """Look up attachment metadata by ID (used by chat route for context injection)."""
    return _registry.get(attachment_id)


@router.post("/upload")
async def upload_attachment(
    file: UploadFile,
    session_id: str = Form(...),
) -> dict:
    """Upload a file and return its attachment_id."""
    session_id = session_id.strip()
    if not session_id or get_chat_session(session_id) is None:
        raise HTTPException(status_code=404, detail="Chat session not found")

    mime = file.content_type or "application/octet-stream"

    # Check image limit before reading data
    if mime.startswith("image/"):
        image_count = sum(
            1 for m in _registry.values()
            if m.session_id == session_id and m.mime_type.startswith("image/")
        )
        if image_count >= _MAX_IMAGES_PER_SESSION:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum {_MAX_IMAGES_PER_SESSION} images per session",
            )

    data = await file.read()
    if len(data) > _MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 200 MB limit")

    attachment_id = uuid4().hex
    safe_name = Path(file.filename or "upload").name
    dest_dir = _UPLOAD_DIR / session_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / f"{attachment_id}_{safe_name}"
    dest_path.write_bytes(data)

    meta = AttachmentMeta(
        id=attachment_id,
        session_id=session_id,
        filename=safe_name,
        mime_type=mime,
        size_bytes=len(data),
        server_path=str(dest_path),
    )
    _registry[attachment_id] = meta

    return {
        "id": attachment_id,
        "filename": safe_name,
        "mime_type": mime,
        "size_bytes": len(data),
        "server_path": str(dest_path),
    }


@router.get("/{attachment_id}")
async def serve_attachment(attachment_id: str, session_id: str) -> FileResponse:
    """Serve an uploaded file for browser display."""
    meta = _registry.get(attachment_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Attachment not found")
    if meta.session_id != session_id:
        raise HTTPException(status_code=403, detail="Access denied")
    if not Path(meta.server_path).exists():
        raise HTTPException(status_code=404, detail="File missing from disk")
    return FileResponse(
        meta.server_path,
        filename=meta.filename,
        media_type=meta.mime_type,
    )
