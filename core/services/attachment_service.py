"""attachment_service — download, store, and read channel attachments.

Shared by discord_gateway and telegram_gateway. Handles all file I/O and
DB persistence so gateways contain no download/storage logic.
"""
from __future__ import annotations

import base64
import logging
import mimetypes
import urllib.request
import uuid
from pathlib import Path
from typing import Any

from core.runtime.config import JARVIS_HOME

logger = logging.getLogger(__name__)

MAX_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
_MAX_TEXT_CHARS = 8_000
_UPLOAD_ROOT = JARVIS_HOME / "uploads"

_ALLOWED_SEND_ROOTS: list[Path] = [
    JARVIS_HOME / "uploads",
    JARVIS_HOME / "workspaces",
]


# ---------------------------------------------------------------------------
# Internal helpers (monkeypatchable in tests)
# ---------------------------------------------------------------------------

_DEFAULT_DOWNLOAD_HEADERS = {
    # Discord CDN (and Telegram via Bot API) reject the default Python-urllib
    # User-Agent as a bot. Use a stable Mozilla UA so attachments fetch.
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
}


def _http_download(url: str, headers: dict[str, str] | None) -> bytes:
    merged = dict(_DEFAULT_DOWNLOAD_HEADERS)
    if headers:
        merged.update(headers)
    req = urllib.request.Request(url, headers=merged)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def _db_store(
    *,
    attachment_id: str,
    session_id: str,
    channel_type: str,
    filename: str,
    mime_type: str,
    size_bytes: int,
    local_path: str,
    source_url: str,
) -> None:
    from core.runtime.db import (
        _ensure_channel_attachments_table,
        connect,
        store_channel_attachment,
    )
    with connect() as conn:
        _ensure_channel_attachments_table(conn)
        store_channel_attachment(
            conn=conn,
            attachment_id=attachment_id,
            session_id=session_id,
            channel_type=channel_type,
            filename=filename,
            mime_type=mime_type,
            size_bytes=size_bytes,
            local_path=local_path,
            source_url=source_url,
        )
        conn.commit()


def _db_get(attachment_id: str) -> dict | None:
    from core.runtime.db import (
        _ensure_channel_attachments_table,
        connect,
        get_channel_attachment,
    )
    with connect() as conn:
        _ensure_channel_attachments_table(conn)
        return get_channel_attachment(conn=conn, attachment_id=attachment_id)


def _db_list(session_id: str, limit: int) -> list[dict]:
    from core.runtime.db import (
        _ensure_channel_attachments_table,
        connect,
        list_channel_attachments,
    )
    with connect() as conn:
        _ensure_channel_attachments_table(conn)
        return list_channel_attachments(conn=conn, session_id=session_id, limit=limit)


def _call_vision(image_b64: str, *, model: str, prompt: str | None = None) -> str:
    from core.services.visual_memory import _describe_via_ollama
    return _describe_via_ollama(image_b64, model=model, prompt=prompt)


def _vision_model() -> str:
    # Pull from runtime.json — single source of truth for which model handles
    # vision. Falls back to a model that actually exists on the local Ollama
    # box (3b, not 7b — 7b was the historical default but isn't installed).
    try:
        from core.runtime.secrets import read_runtime_key
        cfg_model = read_runtime_key("vision_model_name")
        if cfg_model:
            return str(cfg_model)
    except Exception:
        pass
    try:
        from core.services.visual_memory import _DEFAULT_MODEL
        return _DEFAULT_MODEL
    except Exception:
        return "qwen2.5vl:3b"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def download_and_store(
    *,
    url: str,
    filename: str,
    mime_type: str,
    size_bytes: int,
    session_id: str,
    channel_type: str,
    http_headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Download file from URL and persist to uploads/ + DB.

    Returns {"status": "ok", "attachment_id": str, "local_path": str}
         or {"status": "error", "reason": str}
    """
    if size_bytes > MAX_SIZE_BYTES:
        return {"status": "error", "reason": "too_large", "size_bytes": size_bytes}

    attachment_id = str(uuid.uuid4())
    dest_dir = _UPLOAD_ROOT / session_id
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.warning("attachment_service: mkdir failed: %s", exc)
        return {"status": "error", "reason": "disk_error"}

    safe_filename = Path(filename).name or "file"
    local_path = dest_dir / f"{attachment_id}_{safe_filename}"

    try:
        data = _http_download(url, http_headers)
    except Exception as exc:
        logger.warning("attachment_service: download failed for %s: %s", url, exc)
        return {"status": "error", "reason": "download_failed"}

    try:
        local_path.write_bytes(data)
    except OSError as exc:
        logger.warning("attachment_service: write failed: %s", exc)
        return {"status": "error", "reason": "disk_error"}

    if not mime_type:
        mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

    try:
        _db_store(
            attachment_id=attachment_id,
            session_id=session_id,
            channel_type=channel_type,
            filename=safe_filename,
            mime_type=mime_type,
            size_bytes=len(data),
            local_path=str(local_path),
            source_url=url,
        )
    except Exception as exc:
        logger.warning("attachment_service: db store failed: %s", exc)

    return {
        "status": "ok",
        "attachment_id": attachment_id,
        "local_path": str(local_path),
    }


def get_attachment(attachment_id: str) -> dict | None:
    """Return attachment metadata dict, or None if not found."""
    try:
        return _db_get(attachment_id)
    except Exception:
        return None


def list_attachments(session_id: str, limit: int = 20) -> list[dict]:
    """Return recent attachments for session, newest first."""
    try:
        return _db_list(session_id, limit)
    except Exception:
        return []


def read_attachment_content(attachment_id: str) -> dict[str, Any]:
    """Read attachment content for Jarvis.

    image/*         → vision model description
    text/*          → file text (truncated at 8000 chars)
    application/pdf → first 8000 chars via text extraction
    other           → metadata + hex preview
    """
    row = _db_get(attachment_id)
    if row is None:
        return {"status": "error", "reason": "not-found"}

    mime = str(row.get("mime_type") or "")
    local_path = str(row.get("local_path") or "")
    filename = str(row.get("filename") or "")

    if mime.startswith("image/"):
        try:
            data = Path(local_path).read_bytes()
            b64 = base64.b64encode(data).decode("ascii")
            model = _vision_model()
            description = _call_vision(
                b64,
                model=model,
                prompt="Beskriv indholdet af dette billede kortfattet på dansk.",
            )
            return {"status": "ok", "type": "image", "content": description, "filename": filename}
        except Exception as exc:
            logger.warning("attachment_service: vision failed for %s: %s", attachment_id, exc)
            return {
                "status": "ok",
                "type": "image",
                "content": f"[Billede: {filename} — vision fejlede: {exc}]",
                "filename": filename,
            }

    if mime.startswith("text/") or mime == "application/json":
        try:
            text = Path(local_path).read_text(encoding="utf-8", errors="replace")
            return {
                "status": "ok",
                "type": "text",
                "content": text[:_MAX_TEXT_CHARS],
                "filename": filename,
            }
        except Exception as exc:
            return {"status": "error", "reason": f"read-failed: {exc}"}

    if mime == "application/pdf":
        try:
            data = Path(local_path).read_bytes()
            text = data.decode("latin-1", errors="replace")
            printable = "".join(c if c.isprintable() or c in "\n\t" else " " for c in text)
            return {
                "status": "ok",
                "type": "pdf",
                "content": printable[:_MAX_TEXT_CHARS],
                "filename": filename,
            }
        except Exception as exc:
            return {"status": "error", "reason": f"read-failed: {exc}"}

    # Fallback: metadata + hex preview
    try:
        data = Path(local_path).read_bytes()
        preview = data[:64].hex()
    except Exception:
        preview = ""
    return {
        "status": "ok",
        "type": "binary",
        "content": (
            f"Fil: {filename}\nType: {mime}\n"
            f"Størrelse: {row.get('size_bytes', 0)} bytes\n"
            f"Hex preview: {preview}"
        ),
        "filename": filename,
    }


def validate_send_path(path: str) -> tuple[bool, str]:
    """Return (ok, error_message) for outbound file send.

    Checks: path within allowed roots, file exists and readable, under 50 MB.
    """
    p = Path(path).resolve()
    allowed = any(
        str(p).startswith(str(root.resolve()))
        for root in _ALLOWED_SEND_ROOTS
    )
    if not allowed:
        return False, "not-allowed"
    if not p.exists():
        return False, "not-found"
    if not p.is_file():
        return False, "not-a-file"
    size = p.stat().st_size
    if size > MAX_SIZE_BYTES:
        return False, f"file-too-large:{size}"
    return True, ""
