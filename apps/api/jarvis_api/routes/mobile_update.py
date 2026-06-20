"""Mobil auto-updater: manifest + APK-download. Auth-scopet til en bruger.

Læser fra ~/.jarvis-v2/mobile/ (latest.json + APK-fil). Stien resolves ved
kald-tid via JARVIS_HOME, så tests kan override med monkeypatch.setenv.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(tags=["mobile-update"])


def _current_user() -> str | None:
    from core.identity.workspace_context import current_user_id
    return current_user_id() or None


def _mobile_dir() -> Path:
    home = os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2")
    return Path(home) / "mobile"


@router.get("/mobile/latest")
async def mobile_latest() -> dict:
    if not _current_user():
        return {}
    manifest = _mobile_dir() / "latest.json"
    if not manifest.exists():
        return {}
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    return data


@router.get("/mobile/download")
async def mobile_download() -> FileResponse:
    if not _current_user():
        raise HTTPException(status_code=401, detail="auth required")
    manifest = _mobile_dir() / "latest.json"
    if not manifest.exists():
        raise HTTPException(status_code=404, detail="no manifest")
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        filename = Path(str(data.get("filename") or "")).name
    except (ValueError, OSError):
        raise HTTPException(status_code=404, detail="bad manifest")
    if not filename:
        raise HTTPException(status_code=404, detail="no filename")
    apk = _mobile_dir() / filename
    if not apk.exists():
        raise HTTPException(status_code=404, detail="apk missing")
    return FileResponse(
        path=apk,
        filename=filename,
        media_type="application/vnd.android.package-archive",
    )
