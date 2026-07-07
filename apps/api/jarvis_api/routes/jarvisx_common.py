"""Shared constants + guards for the JarvisX route modules.

Extracted from routes/jarvisx.py during the god-file split. Everything
here is imported by the feature-specific submodules AND re-exported from
jarvisx.py so existing import paths keep working.

Behavior-preserving: pure code movement, no logic changes.
"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import HTTPException

from core.identity.workspace_context import current_context_snapshot, current_workspace_name
from core.runtime.config import WORKSPACES_DIR as _WORKSPACES_DIR_RAW

logger = logging.getLogger("apps.api.jarvis_api.routes.jarvisx")

WORKSPACES_DIR = Path(_WORKSPACES_DIR_RAW).resolve()

# Canonical files we always list for a workspace, even when not present.
# Order matters — this is the order they show in the UI.
CANONICAL_FILES: list[tuple[str, str]] = [
    ("MEMORY.md", "Hukommelse"),
    ("MILESTONES.md", "Milepæle"),
    ("USER.md", "Bruger"),
    ("IDENTITY.md", "Identitet"),
    ("SOUL.md", "Sjæl"),
    ("INNER_VOICE.md", "Indre stemme"),
    ("HEARTBEAT.md", "Heartbeat"),
    ("SKILLS.md", "Skills"),
    ("STANDING_ORDERS.md", "Standing orders"),
]

# Allowed file extensions for read. Markdown + plain text only — no
# arbitrary file traversal even if the path validation slips.
SAFE_EXTENSIONS = {".md", ".txt"}

# Caps to keep responses bounded.
MAX_READ_BYTES = 512 * 1024
MAX_DIR_ENTRIES = 200


def _resolve_workspace(name: str | None) -> Path:
    """Resolve a workspace name to its directory, with traversal guard.

    Returns the directory path. Raises 404 if the workspace doesn't
    exist, 400 if the name tries to escape the workspaces root.
    """
    target = (name or current_workspace_name() or "default").strip()
    if not target:
        target = "default"
    candidate = (WORKSPACES_DIR / target).resolve()
    try:
        candidate.relative_to(WORKSPACES_DIR)
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid workspace name")
    if not candidate.is_dir():
        raise HTTPException(status_code=404, detail=f"workspace '{target}' not found")
    return candidate


def _safe_subpath(workspace_dir: Path, relative: str) -> Path:
    """Resolve a relative path under workspace_dir with traversal guard."""
    rel = (relative or "").strip().lstrip("/")
    if not rel:
        raise HTTPException(status_code=400, detail="path required")
    candidate = (workspace_dir / rel).resolve()
    try:
        candidate.relative_to(workspace_dir)
    except ValueError:
        raise HTTPException(status_code=400, detail="path escapes workspace")
    return candidate


def _require_owner() -> None:
    """Raise 403 if the current request isn't from the owner."""
    snap = current_context_snapshot()
    user_id = snap.get("user_id") or ""
    if not user_id:
        # No identity bound — refuse mutating ops.
        raise HTTPException(status_code=403, detail="owner role required")
    try:
        from core.identity.users import find_user_by_discord_id
        u = find_user_by_discord_id(user_id)
    except Exception:
        u = None
    if not u or getattr(u, "role", "") != "owner":
        raise HTTPException(status_code=403, detail="owner role required")
