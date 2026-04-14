"""File download route — serves files Jarvis has published to ~/.jarvis-v2/files/."""
from __future__ import annotations

import mimetypes
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from core.runtime.config import JARVIS_HOME

router = APIRouter(prefix="/files", tags=["files"])

FILES_DIR = JARVIS_HOME / "files"


def ensure_files_dir() -> Path:
    FILES_DIR.mkdir(parents=True, exist_ok=True)
    return FILES_DIR


@router.get("/{filename}")
def download_file(filename: str) -> FileResponse:
    ensure_files_dir()
    # Strip any path traversal attempts
    safe_name = Path(filename).name
    if not safe_name or safe_name != filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    file_path = FILES_DIR / safe_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    mime, _ = mimetypes.guess_type(safe_name)
    return FileResponse(
        path=file_path,
        filename=safe_name,
        media_type=mime or "application/octet-stream",
    )


@router.get("/")
def list_files() -> dict:
    ensure_files_dir()
    files = [
        {"name": f.name, "size_bytes": f.stat().st_size, "url": f"/files/{f.name}"}
        for f in sorted(FILES_DIR.iterdir())
        if f.is_file()
    ]
    return {"files": files, "count": len(files)}
