"""JarvisX workspace + identity/mind route group.

whoami, workspace listing/tree/read, mind snapshot, and owner-only
identity-pin + chronicle mutations. Extracted from routes/jarvisx.py.

Behavior-preserving: pure code movement, no logic changes.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from core.identity.users import load_users
from core.identity.workspace_context import current_workspace_name
from core.runtime.config import WORKSPACES_DIR as _WORKSPACES_DIR_RAW

from apps.api.jarvis_api.routes.jarvisx_common import (
    CANONICAL_FILES,
    MAX_DIR_ENTRIES,
    MAX_READ_BYTES,
    SAFE_EXTENSIONS,
    WORKSPACES_DIR,
    _require_owner,
    _resolve_workspace,
    _safe_subpath,
    logger,
)

router = APIRouter(prefix="/api", tags=["jarvisx"])


@router.get("/whoami")
def whoami() -> dict[str, str | bool]:
    """Return the resolved identity for the current request.

    If the JarvisX user-routing middleware bound a workspace from the
    X-JarvisX-User header, that's what comes back. Same for project
    anchor via X-JarvisX-Project. Otherwise the default context is
    returned — useful for differentiating "no header" from "unknown
    user → public".
    """
    from core.identity.project_context import current_project_root
    from core.identity.users import find_user_by_discord_id
    from core.identity.workspace_context import current_context_snapshot
    snap = current_context_snapshot()
    user_id = snap.get("user_id") or ""
    role = "guest"
    if user_id:
        try:
            u = find_user_by_discord_id(user_id)
            if u:
                role = u.role  # "owner" | "member"
        except Exception:
            pass
    return {
        "workspace": snap.get("workspace") or "default",
        "user_id": user_id,
        "user_display_name": snap.get("user_display_name") or "",
        "header_resolved": bool(user_id),
        "role": role,
        "project_root": current_project_root(),
    }


@router.get("/workspace/list")
def list_workspaces() -> dict[str, Any]:
    """List every directory under workspaces/ with the user (if any)
    that's mapped to it via users.json.
    """
    by_workspace: dict[str, str] = {}
    for u in load_users():
        by_workspace[u.workspace] = u.name
    items: list[dict[str, str]] = []
    if WORKSPACES_DIR.is_dir():
        for entry in sorted(WORKSPACES_DIR.iterdir()):
            if not entry.is_dir():
                continue
            if entry.name.startswith("."):
                continue
            items.append({
                "name": entry.name,
                "owner": by_workspace.get(entry.name, ""),
            })
    return {"workspaces": items, "current": current_workspace_name() or "default"}


@router.get("/workspace/tree")
def workspace_tree(workspace: str | None = Query(default=None)) -> dict[str, Any]:
    """List canonical files + dreams + daily notes for the workspace.

    Always returns canonical entries (with `present: false` for missing
    files) so the UI can show a stable list. Dreams and daily are listed
    sorted by name (dates already sort lexicographically for ISO
    YYYY-MM-DD prefixes).
    """
    ws_dir = _resolve_workspace(workspace)

    canonical: list[dict[str, Any]] = []
    for filename, label in CANONICAL_FILES:
        p = ws_dir / filename
        present = p.is_file()
        canonical.append({
            "name": filename,
            "label": label,
            "present": present,
            "size_bytes": p.stat().st_size if present else 0,
        })

    def _list_dir(dirname: str) -> list[dict[str, Any]]:
        d = ws_dir / dirname
        if not d.is_dir():
            return []
        out: list[dict[str, Any]] = []
        for entry in sorted(d.iterdir(), reverse=True):
            if not entry.is_file():
                continue
            if entry.suffix not in SAFE_EXTENSIONS:
                continue
            out.append({
                "name": entry.name,
                "size_bytes": entry.stat().st_size,
                "modified_at": entry.stat().st_mtime,
            })
            if len(out) >= MAX_DIR_ENTRIES:
                break
        return out

    return {
        "workspace": ws_dir.name,
        "canonical": canonical,
        "dreams": _list_dir("dreams"),
        "daily": _list_dir("memory/daily"),
        "letters": _list_dir("letters"),
    }


@router.get("/workspace/read")
def workspace_read(
    path: str = Query(..., description="Path relative to the workspace root"),
    workspace: str | None = Query(default=None),
) -> dict[str, Any]:
    """Read a markdown / text file from the workspace.

    Capped at 512 KB. Larger files return a truncated payload with a
    flag so the UI can show a "truncated" notice.
    """
    ws_dir = _resolve_workspace(workspace)
    p = _safe_subpath(ws_dir, path)
    if not p.is_file():
        raise HTTPException(status_code=404, detail="file not found")
    if p.suffix not in SAFE_EXTENSIONS:
        raise HTTPException(status_code=400, detail="unsupported file type")
    raw = p.read_bytes()
    truncated = False
    if len(raw) > MAX_READ_BYTES:
        raw = raw[:MAX_READ_BYTES]
        truncated = True
    try:
        text = raw.decode("utf-8", errors="replace")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"decode failed: {exc}")
    return {
        "workspace": ws_dir.name,
        "path": path,
        "content": text,
        "size_bytes": p.stat().st_size,
        "truncated": truncated,
    }


@router.get("/mind/snapshot")
def mind_snapshot() -> dict[str, Any]:
    """One-shot summary of Jarvis's inner state for the Mind view.

    Pulls cognitive_architecture layers, identity pins, recent
    chronicle entries, dreams, and recent council deliberations into
    one payload so the UI can render without 6 separate roundtrips.
    """
    out: dict[str, Any] = {}

    # Cognitive layers from heartbeat state
    try:
        import json as _json
        from core.runtime.workspace_paths import shared_dir
        hb_path = shared_dir() / "runtime" / "HEARTBEAT_STATE.json"
        # Also check legacy flat path (pre-runtime/ subdir era) for compatibility
        if not hb_path.is_file():
            hb_path = shared_dir() / "HEARTBEAT_STATE.json"
        if hb_path.is_file():
            hb = _json.loads(hb_path.read_text(encoding="utf-8"))
            ams = hb.get("affective_meta_state") or {}
            ca = hb.get("cognitive_architecture") or {}
            les = ams.get("live_emotional_state") or {}
            out["affect"] = {
                "state": ams.get("state"),
                "bearing": ams.get("bearing"),
                "monitoring_mode": ams.get("monitoring_mode"),
                "summary": ams.get("summary"),
                "live": {
                    "mood": les.get("mood"),
                    "confidence": les.get("confidence"),
                    "curiosity": les.get("curiosity"),
                    "frustration": les.get("frustration"),
                    "fatigue": les.get("fatigue"),
                    "trust": les.get("trust"),
                    "rhythm_phase": les.get("rhythm_phase"),
                    "rhythm_energy": les.get("rhythm_energy"),
                    "rhythm_social": les.get("rhythm_social"),
                },
            }
            # Personality vector + relationship texture for "humor", "warmth"
            pv = (ca.get("personality_vector") or {}).get("current") or {}
            rt = (ca.get("relationship_texture") or {}).get("current") or {}
            out["personality"] = {
                "humor_frequency": rt.get("humor_frequency"),
                "summary": (ca.get("personality_vector") or {}).get("summary"),
                "communication_style": pv.get("communication_style"),
                "current_bearing": pv.get("current_bearing"),
            }
            # Each cognitive layer's snapshot summary if available
            layer_keys = [
                "mood_oscillator", "valence_trajectory", "relational_warmth",
                "relation_dynamics", "developmental_valence", "existential_drift",
                "rhythm", "temporal_rhythm", "infra_weather",
            ]
            out["layers"] = {
                k: (ca.get(k) or {}).get("summary")
                for k in layer_keys
                if (ca.get(k) or {}).get("summary")
            }
    except Exception as exc:
        logger.debug("mind_snapshot: heartbeat read failed: %s", exc)

    # Identity pins
    try:
        from core.tools.identity_pin_tools import list_pins
        out["pins"] = list_pins()
    except Exception:
        out["pins"] = []

    # Recent chronicle entries (workspace-scoped)
    try:
        from core.identity.workspace_context import current_workspace_name
        ws = current_workspace_name() or "default"
        chron_dir = Path(_WORKSPACES_DIR_RAW) / ws / "chronicle"
        chron: list[dict[str, Any]] = []
        if chron_dir.is_dir():
            for entry in sorted(chron_dir.iterdir(), reverse=True)[:5]:
                if not entry.is_file() or entry.suffix not in {".md", ".txt"}:
                    continue
                try:
                    raw = entry.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue
                chron.append({
                    "name": entry.name,
                    "modified_at": entry.stat().st_mtime,
                    "preview": raw[:600],
                })
        out["chronicle"] = chron
    except Exception:
        out["chronicle"] = []

    # Recent dreams
    try:
        from core.identity.workspace_context import current_workspace_name
        ws = current_workspace_name() or "default"
        dream_dir = Path(_WORKSPACES_DIR_RAW) / ws / "dreams"
        dreams: list[dict[str, Any]] = []
        if dream_dir.is_dir():
            for entry in sorted(dream_dir.iterdir(), reverse=True)[:8]:
                if not entry.is_file() or entry.suffix not in {".md", ".txt"}:
                    continue
                try:
                    raw = entry.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue
                dreams.append({
                    "name": entry.name,
                    "modified_at": entry.stat().st_mtime,
                    "preview": raw[:500],
                })
        out["dreams"] = dreams
    except Exception:
        out["dreams"] = []

    # MILESTONES preview (first ~1500 chars)
    try:
        from core.identity.workspace_context import current_workspace_name
        ws = current_workspace_name() or "default"
        ms_path = Path(_WORKSPACES_DIR_RAW) / ws / "MILESTONES.md"
        from core.services.workspace_crypto import read_text_for_path
        raw = read_text_for_path(ms_path)
        if raw is not None:
            out["milestones_preview"] = raw[:1500]
    except Exception:
        pass

    return out


# ── Identity pin + chronicle mutations (owner-only) ───────────────
# Lets JarvisX' Mind view drive write-side actions Bjørn previously
# could only trigger through tool calls Jarvis ran on his behalf.


class _PinPayload(BaseModel):
    title: str
    content: str
    source: str | None = None


@router.post("/identity-pins")
def add_identity_pin(payload: _PinPayload) -> dict[str, Any]:
    """Pin a piece of text as permanent awareness. Owner-only.

    Mirrors the pin_identity tool but lets Bjørn pin from the Mind UI
    directly. pinned_by is recorded as 'user' so Jarvis can tell at a
    glance which pins came from him vs Bjørn.
    """
    _require_owner()
    from core.tools.identity_pin_tools import add_pin
    out = add_pin(
        title=payload.title,
        content=payload.content,
        source=(payload.source or "manual"),
        pinned_by="user",
    )
    if out.get("status") != "ok":
        raise HTTPException(status_code=400, detail=out.get("error") or "pin failed")
    return out


@router.delete("/identity-pins/{pin_id}")
def remove_identity_pin(pin_id: str) -> dict[str, Any]:
    """Unpin by pin_id. Owner-only."""
    _require_owner()
    from core.tools.identity_pin_tools import remove_pin
    out = remove_pin(pin_id)
    if out.get("status") != "ok":
        raise HTTPException(status_code=404, detail=out.get("error") or "pin not found")
    return out


class _ChroniclePayload(BaseModel):
    title: str
    content: str
    workspace: str | None = None


@router.post("/chronicle")
def write_chronicle_entry(payload: _ChroniclePayload) -> dict[str, Any]:
    """Append a new chronicle entry to the workspace's chronicle/ dir.

    Owner-only. Writes a date-prefixed markdown file. If a file with
    the same date+slug exists, suffixes -2, -3, etc. so we never
    silently overwrite Jarvis' own entries.
    """
    _require_owner()
    title = payload.title.strip()
    content = payload.content.strip()
    if not title or not content:
        raise HTTPException(status_code=400, detail="title and content required")
    ws_dir = _resolve_workspace(payload.workspace)
    chron_dir = ws_dir / "chronicle"
    chron_dir.mkdir(parents=True, exist_ok=True)

    # Date-prefixed filename, slug from title (alnum + hyphens, lowercased)
    date = datetime.utcnow().strftime("%Y-%m-%d")
    slug = "".join(c.lower() if c.isalnum() else "-" for c in title)
    slug = "-".join(filter(None, slug.split("-")))[:60] or "entry"
    base = f"{date}-{slug}"
    suffix = ""
    counter = 2
    while (chron_dir / f"{base}{suffix}.md").exists():
        suffix = f"-{counter}"
        counter += 1
    out_path = chron_dir / f"{base}{suffix}.md"

    body = f"# {title}\n\n*written by user via JarvisX · {datetime.utcnow().isoformat()}Z*\n\n{content}\n"
    out_path.write_text(body, encoding="utf-8")
    return {
        "status": "ok",
        "name": out_path.name,
        "workspace": ws_dir.name,
        "size_bytes": out_path.stat().st_size,
    }
