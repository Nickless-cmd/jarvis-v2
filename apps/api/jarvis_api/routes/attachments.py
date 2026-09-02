"""Attachment upload and serve endpoints.

Files are saved to ~/.jarvis-v2/uploads/{session_id}/{uuid}_{filename}.
Metadata is kept in an in-memory registry (_registry) — lost on server restart,
which is acceptable for session-scoped attachments.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from core.services.chat_sessions import get_chat_session

logger = logging.getLogger(__name__)

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
    """Look up attachment metadata by ID (used by chat route for context injection).

    Kigger i hukommelses-registret FØRST og derefter i DB'en. Registret er hurtigt
    men dør med processen; DB-posten overlever genstart. Uden fallback'et
    forsvandt en vedhæftning fra en samtale, så snart api'en var genstartet —
    filen lå der stadig, men ingen kunne finde den.
    """
    hit = _registry.get(attachment_id)
    if hit is not None:
        return hit
    try:
        from core.services.attachment_service import get_attachment as _db_get
        row = _db_get(attachment_id)
    except Exception:
        row = None
    if not row:
        return None
    return AttachmentMeta(
        id=str(row.get("attachment_id") or attachment_id),
        session_id=str(row.get("session_id") or ""),
        filename=str(row.get("filename") or "fil"),
        mime_type=str(row.get("mime_type") or "application/octet-stream"),
        size_bytes=int(row.get("size_bytes") or 0),
        server_path=str(row.get("local_path") or ""),
    )


def get_attachment_meta_dicts(attachment_ids: list[str]) -> list[dict]:
    """Metadata som dicts, i den rækkefølge de blev vedhæftet.

    Bruges af chat-ruten til at lægge billed-referencer på brugerens besked.
    Ukendte id'er springes over frem for at give en tom plads klienten aldrig
    kan fylde.
    """
    out: list[dict] = []
    for aid in attachment_ids or []:
        meta = get_attachment(str(aid or "").strip())
        if meta is None:
            continue
        out.append({
            "id": meta.id,
            "filename": meta.filename,
            "mime_type": meta.mime_type,
            "size_bytes": meta.size_bytes,
        })
    return out


def apply_attachment_context(message: str, attachment_ids: list[str] | None) -> str:
    """Prepend en attachment-direktiv-blok til beskeden, så Jarvis ved HVORDAN han
    ser filen (analyze_image / read_file med den eksakte server-sti). Delt mellem
    /chat/stream (v1) og /chat/stream/v2 så vision virker ens begge steder.
    Uden direktivet læser modellen "[Attached files: ...]" som flavour-tekst og
    påstår den ikke kan se billeder.
    """
    if not attachment_ids:
        return message
    image_lines: list[str] = []
    other_lines: list[str] = []
    for aid in attachment_ids:
        meta = get_attachment(aid)
        if not meta:
            continue
        if meta.mime_type.startswith("image/"):
            image_lines.append(
                f"To see the image '{meta.filename}', call:\n"
                f"  analyze_image(image_path={meta.server_path!r})\n"
                f"Use that exact absolute path verbatim — do not abbreviate it."
            )
        else:
            other_lines.append(
                f"To read the file '{meta.filename}', call:\n"
                f"  read_file(path={meta.server_path!r})"
            )
    prefix_parts: list[str] = []
    if image_lines:
        prefix_parts.append(
            "[The user attached image(s) to this message. You CAN see images by "
            "using the analyze_image tool. Do NOT claim you cannot see images — "
            "the tool exists and works.]\n\n" + "\n\n".join(image_lines)
        )
    if other_lines:
        prefix_parts.append("[The user attached file(s):]\n\n" + "\n\n".join(other_lines))
    if not prefix_parts:
        return message
    return "\n\n".join(prefix_parts) + "\n\n---\n\n" + message


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

    # A1 (2026-06-22): malware-scan GENNEM Den Intelligente Central (execution🔒, SECURITY).
    # Scanneren var bygget men UWIRET — uploads blev skrevet til disk uscannede. Infected →
    # slet filen + afvis. ClamAV-utilgængelig → fail-open (blokerer ikke legitime uploads).
    try:
        from core.services.gate_execution import check_upload
        _scan = check_upload(str(dest_path))
    except Exception as _scan_exc:
        _scan = None
        # Fail-open synlighed (audit 2026-07-04): kaster scan-stien springes malware-scan
        # OVER og uploaden tillades — det er en SECURITY fail-open og MÅ ikke være tavs.
        # Flag incidenten, men bevar fail-open-adfærden (_scan=None → upload igennem).
        # Self-safe: incident-loggen kaster aldrig.
        try:
            from core.runtime.db_central_incidents import record_central_incident
            record_central_incident(
                cluster="execution", nerve="upload_scan", kind="fail_open",
                severity="error",
                message=f"check_upload kastede → malware-scan SPRUNGET OVER (upload tilladt) "
                        f"for {dest_path.name}: {type(_scan_exc).__name__}: {_scan_exc}"[:300],
                session_id=str(session_id or ""),
            )
        except Exception:
            pass
    if _scan is not None and not _scan.allowed:
        try:
            dest_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise HTTPException(
            status_code=400,
            detail=f"Upload afvist af malware-scan: {_scan.reason or 'infected'}",
        )

    meta = AttachmentMeta(
        id=attachment_id,
        session_id=session_id,
        filename=safe_name,
        mime_type=mime,
        size_bytes=len(data),
        server_path=str(dest_path),
    )
    _registry[attachment_id] = meta

    # Gør posten holdbar. Registret ovenfor er processens korttidshukommelse;
    # uden en DB-post var en vedhæftning glemt ved næste genstart, og beskeden
    # der henviste til den pegede ud i ingenting. Self-safe: fejler skrivningen,
    # er uploaden stadig lykkedes — den overlever bare ikke en genstart.
    try:
        from core.services.attachment_service import _db_store
        _db_store(
            attachment_id=attachment_id,
            session_id=session_id,
            channel_type="upload",
            filename=safe_name,
            mime_type=mime,
            size_bytes=len(data),
            local_path=str(dest_path),
            source_url="",
        )
    except Exception as _store_exc:
        logger.warning("attachment %s ikke persisteret: %s", attachment_id[:8], _store_exc)

    return {
        "id": attachment_id,
        "filename": safe_name,
        "mime_type": mime,
        "size_bytes": len(data),
        "server_path": str(dest_path),
    }


# Registreres FØR /{attachment_id} så "images"/"image" ikke fanges som id.
@router.get("/images")
async def list_images(limit: int = 200) -> dict:
    """Galleri-liste (#6): billed-attachments på tværs af sessioner, user-scopet."""
    from core.identity.workspace_context import current_user_id
    from core.services.attachment_service import list_image_attachments
    uid = current_user_id() or None
    return {"items": list_image_attachments(user_id=uid, limit=limit)}


@router.get("/image/{attachment_id}")
async def serve_image_from_db(attachment_id: str) -> FileResponse:
    """Serve et billede fra DB'ens local_path (virker for historiske billeder
    — i modsætning til /{attachment_id} der kun kender denne sessions registry).
    User-scopet: kun billeder fra sessioner brugeren deltog i."""
    from core.identity.workspace_context import current_user_id
    from core.services.attachment_service import (
        get_attachment, attachment_visible_to_user,
    )
    uid = current_user_id() or None
    if not attachment_visible_to_user(attachment_id, uid):
        raise HTTPException(status_code=403, detail="Access denied")
    row = get_attachment(attachment_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Attachment not found")
    local_path = str(row.get("local_path") or "")
    if not local_path or not Path(local_path).exists():
        raise HTTPException(status_code=404, detail="File missing from disk")
    return FileResponse(
        local_path,
        filename=str(row.get("filename") or "image"),
        media_type=str(row.get("mime_type") or "application/octet-stream"),
    )


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
