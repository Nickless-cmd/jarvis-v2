"""JarvisX-specific routes — small endpoints used by the desktop app.

Endpoints:
  /api/whoami            — which workspace did the X-JarvisX-User header
                           resolve to (verifies user-routing middleware)
  /api/workspace/tree    — list canonical workspace files + dreams + daily
  /api/workspace/read    — fetch a single workspace file's content
  /api/workspace/list    — list all available workspaces (for switcher)
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from core.identity.users import load_users
from core.identity.workspace_context import current_context_snapshot, current_workspace_name
from core.runtime.config import WORKSPACES_DIR as _WORKSPACES_DIR_RAW

logger = logging.getLogger(__name__)

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


@router.get("/channels/state")
def channels_state() -> dict[str, Any]:
    """Aggregate gateway status for the Channels view.

    Pulls live in-memory status from each gateway module (Discord +
    Telegram) plus the runtime KV mirror so we get the same truth even
    when read from a different worker process.
    """
    out: dict[str, Any] = {"channels": []}
    # Discord — read from runtime_state_kv mirror so we get the runtime
    # worker's truth even when the API worker handles the request.
    try:
        from core.runtime.db import get_runtime_state_value
        from core.services.discord_config import is_discord_configured
        kv = get_runtime_state_value("discord_gateway.status") or {}
        if isinstance(kv, str):
            import json as _json
            try:
                kv = _json.loads(kv)
            except Exception:
                kv = {}
        out["channels"].append({
            "id": "discord",
            "label": "Discord",
            "configured": is_discord_configured(),
            "connected": bool(kv.get("connected")),
            "last_message_at": kv.get("last_message_at"),
            "message_count": kv.get("message_count", 0),
            "guild_name": kv.get("guild_name"),
            "error": kv.get("connect_error"),
        })
    except Exception as exc:
        logger.debug("channels_state: discord read failed: %s", exc)
        out["channels"].append({
            "id": "discord", "label": "Discord", "configured": False,
            "connected": False, "error": str(exc),
        })
    # Telegram
    try:
        from core.services.telegram_gateway import get_status as tg_status, is_configured as tg_configured
        s = tg_status()
        out["channels"].append({
            "id": "telegram",
            "label": "Telegram",
            "configured": tg_configured(),
            "connected": bool(s.get("connected")),
            "last_message_at": s.get("last_message_at"),
            "message_count": s.get("message_count", 0),
            "active_sessions": s.get("active_sessions", 0),
            "error": s.get("error"),
        })
    except Exception as exc:
        logger.debug("channels_state: telegram read failed: %s", exc)
        out["channels"].append({
            "id": "telegram", "label": "Telegram", "configured": False,
            "connected": False, "error": str(exc),
        })
    # Webchat (always present — it's the API itself)
    try:
        from core.services.chat_sessions import list_chat_sessions
        sessions = list_chat_sessions() or []
        out["channels"].append({
            "id": "webchat",
            "label": "Webchat",
            "configured": True,
            "connected": True,
            "session_count": len(sessions),
            "last_message_at": (
                sessions[0].get("updated_at") if sessions else None
            ),
        })
    except Exception as exc:
        logger.debug("channels_state: webchat read failed: %s", exc)
    return out


@router.get("/scheduling/state")
def scheduling_state() -> dict[str, Any]:
    """Aggregate scheduled tasks + recurring + self-wakeups."""
    out: dict[str, Any] = {}
    try:
        from core.services.scheduled_tasks import get_scheduled_tasks_state
        out["scheduled"] = get_scheduled_tasks_state()
    except Exception as exc:
        logger.debug("scheduling_state: scheduled failed: %s", exc)
        out["scheduled"] = {"error": str(exc)}
    try:
        from core.services.recurring_tasks import get_recurring_tasks_state
        out["recurring"] = get_recurring_tasks_state()
    except Exception as exc:
        logger.debug("scheduling_state: recurring failed: %s", exc)
        out["recurring"] = {"error": str(exc)}
    try:
        from core.services.self_wakeup import list_wakeups
        out["wakeups"] = {
            "pending": list_wakeups(status="pending", limit=20),
            "fired": list_wakeups(status="fired", limit=10),
            "consumed": list_wakeups(status="consumed", limit=5),
        }
    except Exception as exc:
        logger.debug("scheduling_state: wakeups failed: %s", exc)
        out["wakeups"] = {"error": str(exc)}
    return out


# ── Project anchor: tree, read, notes ─────────────────────────────

# Skip these directories when walking a project tree — they're huge and
# never relevant for human-driven file exploration. Mirrors what most
# IDEs hide by default.
_PROJECT_TREE_SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "dist", "build", ".cache", ".next", ".vite-cache", "release",
    ".pytest_cache", ".mypy_cache", "target", ".gradle",
}
_PROJECT_TREE_MAX_ENTRIES = 5000  # safety cap per request
_PROJECT_READ_MAX_BYTES = 1024 * 1024  # 1 MB ceiling for in-app preview


def _resolve_project_root(root: str) -> Path:
    """Resolve a project root with strict guards.

    The project anchor can be ANYWHERE on the host — not constrained to
    ~/.jarvis-v2/workspaces/ like the multi-user workspace API. So
    instead of a workspace allowlist we apply path normalization +
    refuse to descend into obvious system roots without explicit intent.
    """
    if not root or not root.strip():
        raise HTTPException(status_code=400, detail="root required")
    p = Path(root).expanduser().resolve()
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"path not found: {p}")
    if not p.is_dir():
        raise HTTPException(status_code=400, detail="root is not a directory")
    # Refuse to root at filesystem boundaries that have no business being
    # called "a project". Users can still hit them via direct read_file.
    forbidden = {Path("/"), Path("/etc"), Path("/var"), Path("/usr"), Path("/proc"), Path("/sys")}
    if p in forbidden:
        raise HTTPException(status_code=400, detail=f"cannot use {p} as project root")
    return p


def _safe_project_subpath(root: Path, rel: str) -> Path:
    """Resolve a relative path under the project root, refusing escapes."""
    if not rel:
        raise HTTPException(status_code=400, detail="path required")
    candidate = (root / rel.lstrip("/")).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        raise HTTPException(status_code=400, detail="path escapes project root")
    return candidate


@router.get("/project/tree")
def project_tree(
    root: str = Query(..., description="Absolute project root path"),
    max_depth: int = Query(default=4, ge=1, le=8),
) -> dict[str, Any]:
    """Return a nested tree of the project root, depth-limited."""
    root_path = _resolve_project_root(root)

    counter = {"n": 0}

    def walk(d: Path, depth: int) -> dict[str, Any]:
        node: dict[str, Any] = {
            "name": d.name or str(d),
            "kind": "dir",
            "path": str(d),
            "children": [],
        }
        if depth >= max_depth:
            node["truncated"] = True
            return node
        try:
            entries = sorted(d.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
        except PermissionError:
            node["error"] = "permission denied"
            return node
        for entry in entries:
            counter["n"] += 1
            if counter["n"] > _PROJECT_TREE_MAX_ENTRIES:
                node["truncated"] = True
                break
            if entry.is_dir():
                if entry.name in _PROJECT_TREE_SKIP_DIRS or entry.name.startswith(".jarvisx"):
                    # Skip skiplist + the .jarvisx directory used for notes
                    # to keep noise low. Notes are exposed via /api/project/notes.
                    if entry.name == ".jarvisx":
                        continue
                    if entry.name in _PROJECT_TREE_SKIP_DIRS:
                        # Show as collapsed placeholder so user knows it's there
                        node["children"].append({
                            "name": entry.name,
                            "kind": "dir",
                            "path": str(entry),
                            "skipped": True,
                        })
                        continue
                node["children"].append(walk(entry, depth + 1))
            else:
                try:
                    size = entry.stat().st_size
                except Exception:
                    size = None
                node["children"].append({
                    "name": entry.name,
                    "kind": "file",
                    "path": str(entry),
                    "size_bytes": size,
                })
        return node

    return {"root": str(root_path), "tree": walk(root_path, 0), "entry_count": counter["n"]}


@router.get("/project/list")
def project_list(
    root: str = Query(..., description="Absolute project root path"),
    limit: int = Query(default=2000, ge=1, le=10000),
) -> dict[str, Any]:
    """Flat list of files under root (for @file autocomplete).

    Walks the tree once, returns just paths + sizes — no nesting. Used
    by the composer's @file completion to fuzzy-match.
    """
    root_path = _resolve_project_root(root)
    files: list[dict[str, Any]] = []

    def walk(d: Path) -> None:
        if len(files) >= limit:
            return
        try:
            entries = list(d.iterdir())
        except PermissionError:
            return
        for entry in entries:
            if len(files) >= limit:
                return
            if entry.is_dir():
                if entry.name in _PROJECT_TREE_SKIP_DIRS or entry.name.startswith(".jarvisx"):
                    continue
                walk(entry)
            elif entry.is_file():
                try:
                    rel = str(entry.relative_to(root_path))
                except Exception:
                    continue
                files.append({
                    "path": str(entry),
                    "rel": rel,
                    "size_bytes": entry.stat().st_size,
                })

    walk(root_path)
    return {"root": str(root_path), "count": len(files), "files": files}


@router.get("/project/read")
def project_read(
    root: str = Query(...),
    path: str = Query(..., description="Path relative to root (or absolute under root)"),
) -> dict[str, Any]:
    """Read a file from inside the project root with a 1 MB cap."""
    root_path = _resolve_project_root(root)
    # Accept both absolute paths under root and relative paths
    if path.startswith("/"):
        target = Path(path).expanduser().resolve()
        try:
            target.relative_to(root_path)
        except ValueError:
            raise HTTPException(status_code=400, detail="path outside project root")
    else:
        target = _safe_project_subpath(root_path, path)
    if not target.is_file():
        raise HTTPException(status_code=404, detail="file not found")
    raw = target.read_bytes()
    truncated = False
    if len(raw) > _PROJECT_READ_MAX_BYTES:
        raw = raw[:_PROJECT_READ_MAX_BYTES]
        truncated = True
    try:
        text = raw.decode("utf-8", errors="replace")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"decode failed: {exc}")
    try:
        rel = str(target.relative_to(root_path))
    except Exception:
        rel = str(target)
    return {
        "root": str(root_path),
        "path": str(target),
        "rel": rel,
        "content": text,
        "size_bytes": target.stat().st_size,
        "truncated": truncated,
    }


@router.get("/project/notes")
def project_notes_get(root: str = Query(...)) -> dict[str, Any]:
    """Read .jarvisx/notes.md inside the anchored project, if it exists.

    This is project-specific persistent memory: when the same project is
    re-anchored later, prompt_contract reads this back into awareness so
    Jarvis "remembers" lessons learned about THIS codebase across
    sessions. Empty content if the file doesn't exist yet.
    """
    root_path = _resolve_project_root(root)
    notes_path = root_path / ".jarvisx" / "notes.md"
    if not notes_path.is_file():
        return {"root": str(root_path), "exists": False, "content": ""}
    raw = notes_path.read_bytes()
    if len(raw) > _PROJECT_READ_MAX_BYTES:
        raw = raw[:_PROJECT_READ_MAX_BYTES]
    return {
        "root": str(root_path),
        "exists": True,
        "content": raw.decode("utf-8", errors="replace"),
        "size_bytes": notes_path.stat().st_size,
        "modified_at": notes_path.stat().st_mtime,
    }


class ProjectNotesUpdate(BaseModel):
    root: str
    content: str


@router.post("/project/notes")
def project_notes_set(payload: ProjectNotesUpdate) -> dict[str, Any]:
    """Write .jarvisx/notes.md inside the anchored project."""
    root_path = _resolve_project_root(payload.root)
    notes_dir = root_path / ".jarvisx"
    notes_dir.mkdir(exist_ok=True)
    notes_path = notes_dir / "notes.md"
    notes_path.write_text(payload.content, encoding="utf-8")
    # Make sure .gitignore in .jarvisx ignores its own dir contents from
    # accidentally being committed — we don't enforce it but we hint.
    gi = notes_dir / ".gitignore"
    if not gi.exists():
        gi.write_text("# JarvisX local-only notes — do not commit\n*\n!.gitignore\n", encoding="utf-8")
    return {
        "status": "ok",
        "path": str(notes_path),
        "size_bytes": notes_path.stat().st_size,
    }


# ── File watch (mtime-polling v1) ─────────────────────────────────

# In-memory watch state. Keyed by session_id; each session can watch
# multiple files/dirs and we surface "what changed since last poll" via
# /api/project/watch/poll. mtime-based — less efficient than inotify but
# zero deps and works on any filesystem.
_watch_state: dict[str, dict[str, dict[str, Any]]] = {}
_watch_lock_holder: list[Any] = []


def _watch_lock() -> Any:
    if not _watch_lock_holder:
        import threading as _t
        _watch_lock_holder.append(_t.Lock())
    return _watch_lock_holder[0]


class WatchAddRequest(BaseModel):
    session_id: str
    paths: list[str]


class WatchPollRequest(BaseModel):
    session_id: str


@router.post("/project/watch/add")
def project_watch_add(payload: WatchAddRequest) -> dict[str, Any]:
    """Start watching a list of files/dirs for the session.

    Returns the initial mtimes — subsequent /poll calls return only
    changes since the last poll.
    """
    with _watch_lock():
        sess = _watch_state.setdefault(payload.session_id, {})
        added: list[dict[str, Any]] = []
        for raw_path in payload.paths:
            try:
                p = Path(raw_path).expanduser().resolve()
                if not p.exists():
                    continue
                mtime = p.stat().st_mtime
                size = p.stat().st_size if p.is_file() else None
                sess[str(p)] = {
                    "path": str(p),
                    "is_file": p.is_file(),
                    "mtime": mtime,
                    "size": size,
                    "last_change_seen_at": None,
                }
                added.append({"path": str(p), "mtime": mtime})
            except Exception as exc:
                logger.debug("watch_add: %s failed: %s", raw_path, exc)
    return {"status": "ok", "watching": added, "total": len(added)}


@router.post("/project/watch/poll")
def project_watch_poll(payload: WatchPollRequest) -> dict[str, Any]:
    """Return the list of watched paths whose mtime changed since last poll."""
    changes: list[dict[str, Any]] = []
    now = datetime.now().timestamp() if False else None  # placeholder — use raw mtime
    with _watch_lock():
        sess = _watch_state.get(payload.session_id, {})
        for path_str, entry in list(sess.items()):
            p = Path(path_str)
            if not p.exists():
                # File was deleted since last check
                changes.append({"path": path_str, "kind": "deleted"})
                sess.pop(path_str, None)
                continue
            try:
                cur_mtime = p.stat().st_mtime
            except Exception:
                continue
            if cur_mtime > entry["mtime"]:
                changes.append({
                    "path": path_str,
                    "kind": "modified",
                    "old_mtime": entry["mtime"],
                    "new_mtime": cur_mtime,
                    "size": p.stat().st_size if p.is_file() else None,
                })
                entry["mtime"] = cur_mtime
                entry["size"] = p.stat().st_size if p.is_file() else None
        # Touch — silence "now" warning above
        _ = now
    return {"changes": changes, "watched_count": len(_watch_state.get(payload.session_id, {}))}


@router.post("/project/watch/clear")
def project_watch_clear(payload: WatchPollRequest) -> dict[str, Any]:
    """Stop all watches for a session."""
    with _watch_lock():
        _watch_state.pop(payload.session_id, None)
    return {"status": "ok"}


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
        from core.runtime.config import JARVIS_HOME
        hb_path = Path(JARVIS_HOME) / "workspaces" / "default" / "runtime" / "HEARTBEAT_STATE.json"
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
        if ms_path.is_file():
            raw = ms_path.read_text(encoding="utf-8", errors="replace")
            out["milestones_preview"] = raw[:1500]
    except Exception:
        pass

    return out


@router.get("/preferences")
def preferences_get() -> dict[str, Any]:
    """User-level UI preferences (output style, tool permissions, etc).

    Stored in JARVIS_HOME/config/jarvisx_prefs.json so they survive
    runtime restarts and apply across sessions.
    """
    from core.runtime.config import CONFIG_DIR
    p = Path(CONFIG_DIR) / "jarvisx_prefs.json"
    if not p.is_file():
        return {"output_style": "balanced", "tool_permissions": {}}
    import json as _json
    try:
        data = _json.loads(p.read_text(encoding="utf-8"))
        return {
            "output_style": str(data.get("output_style") or "balanced"),
            "tool_permissions": data.get("tool_permissions") if isinstance(data.get("tool_permissions"), dict) else {},
        }
    except Exception:
        return {"output_style": "balanced", "tool_permissions": {}}


class PreferencesUpdate(BaseModel):
    output_style: str | None = None
    tool_permissions: dict[str, str] | None = None


@router.post("/preferences")
def preferences_set(payload: PreferencesUpdate) -> dict[str, Any]:
    from core.runtime.config import CONFIG_DIR
    import json as _json
    p = Path(CONFIG_DIR) / "jarvisx_prefs.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    current: dict[str, Any] = {}
    if p.is_file():
        try:
            current = _json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            current = {}
    if payload.output_style is not None:
        if payload.output_style in {"concise", "balanced", "detailed", "technical"}:
            current["output_style"] = payload.output_style
    if payload.tool_permissions is not None:
        # Validate values
        valid = {}
        for k, v in payload.tool_permissions.items():
            if v in {"allow", "deny", "ask"}:
                valid[str(k)] = v
        current["tool_permissions"] = valid
    p.write_text(_json.dumps(current, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"status": "ok", "preferences": current}


@router.get("/tools/inventory")
def tools_inventory() -> dict[str, Any]:
    """Return the full tool catalog with name + description + required params.
    Used by the JarvisX 'tool inventory' modal."""
    try:
        from core.tools.simple_tools import TOOL_DEFINITIONS as defs
    except Exception:
        defs = []
    items: list[dict[str, Any]] = []
    for d in defs:
        fn = d.get("function") if isinstance(d, dict) else None
        if not isinstance(fn, dict):
            continue
        name = str(fn.get("name") or "")
        if not name:
            continue
        params = fn.get("parameters") or {}
        required = list(params.get("required", [])) if isinstance(params, dict) else []
        items.append({
            "name": name,
            "description": str(fn.get("description") or "")[:600],
            "required": required,
        })
    items.sort(key=lambda x: x["name"])
    return {"count": len(items), "tools": items}


@router.get("/todos")
def todos_list(session_id: str = Query(..., description="Session id")) -> dict[str, Any]:
    """List todos for a session — used by JarvisX's TodoPanel UI."""
    from core.services.agent_todos import list_todos
    items = list_todos(session_id)
    return {"session_id": session_id, "count": len(items), "todos": items}


class TodoStatusUpdate(BaseModel):
    session_id: str
    todo_id: str
    status: str


@router.post("/todos/status")
def todos_status(payload: TodoStatusUpdate) -> dict[str, Any]:
    from core.services.agent_todos import update_todo_status
    return update_todo_status(payload.session_id, payload.todo_id, payload.status)


@router.get("/chat/search")
def chat_search(
    q: str = Query(..., min_length=1, max_length=200, description="Search query"),
    limit: int = Query(default=60, ge=1, le=300),
    scope: str = Query(default="all", description="all|current_workspace"),
) -> dict[str, Any]:
    """Full-text search across chat_messages.

    Returns hits with their session_id, message snippet, role, time.
    Used by JarvisX's Cmd-K search modal to jump across sessions.

    Default scope=all returns everyone's hits — JarvisX UI typically
    filters to current workspace via the `current_workspace` scope which
    reads the bound workspace from the user-routing middleware.
    """
    from core.runtime.config import JARVIS_HOME
    import sqlite3
    db_path = Path(JARVIS_HOME) / "state" / "jarvis.db"
    if not db_path.is_file():
        return {"hits": [], "count": 0}
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        like = f"%{q}%"
        params: list[Any] = [like]
        clause = "content LIKE ?"
        if scope == "current_workspace":
            from core.identity.workspace_context import current_workspace_name
            ws = current_workspace_name() or "default"
            clause += " AND workspace_name = ?"
            params.append(ws)
        params.append(int(limit))
        rows = conn.execute(
            f"""
            SELECT message_id, session_id, role, content, created_at,
                   user_id, workspace_name
            FROM chat_messages
            WHERE {clause}
            ORDER BY id DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
        # Also pull the session titles so the UI can show context
        session_ids = sorted({r["session_id"] for r in rows})
        title_map: dict[str, str] = {}
        if session_ids:
            placeholders = ",".join("?" * len(session_ids))
            try:
                trows = conn.execute(
                    f"SELECT id, title FROM chat_sessions WHERE id IN ({placeholders})",
                    session_ids,
                ).fetchall()
                for tr in trows:
                    title_map[tr["id"]] = tr["title"]
            except Exception:
                # chat_sessions table layout may differ; fall back silently
                pass
    finally:
        conn.close()

    hits = []
    q_low = q.lower()
    for r in rows:
        content = r["content"] or ""
        # Build a short snippet centered on the match
        idx = content.lower().find(q_low)
        if idx < 0:
            snippet = content[:160]
        else:
            start = max(0, idx - 40)
            end = min(len(content), idx + len(q) + 80)
            snippet = ("…" if start > 0 else "") + content[start:end] + ("…" if end < len(content) else "")
        hits.append({
            "message_id": r["message_id"],
            "session_id": r["session_id"],
            "session_title": title_map.get(r["session_id"], ""),
            "role": r["role"],
            "snippet": snippet,
            "created_at": r["created_at"],
            "user_id": r["user_id"],
            "workspace_name": r["workspace_name"],
        })
    return {"q": q, "scope": scope, "count": len(hits), "hits": hits}


@router.get("/staged-edits")
def staged_edits(session_id: str = Query(..., description="Chat session id")) -> dict[str, Any]:
    """List staged edits for a session, including full diffs.

    Used by JarvisX's StagedEditsStrip + diff panel to show what's
    pending without round-tripping through Jarvis.
    """
    from core.services.staged_edits import list_staged
    return list_staged(session_id, full_diffs=True)


@router.post("/staged-edits/commit")
def staged_edits_commit(
    session_id: str = Query(...),
    stage_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Apply staged edits. Same as the commit_staged_edits tool, but
    callable from the UI without going through Jarvis."""
    from core.services.staged_edits import commit_staged
    return commit_staged(session_id, stage_ids=stage_ids)


@router.post("/staged-edits/discard")
def staged_edits_discard(
    session_id: str = Query(...),
    stage_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Drop staged edits without applying."""
    from core.services.staged_edits import discard_staged
    return discard_staged(session_id, stage_ids=stage_ids)


@router.get("/tool-result/{result_id}")
def get_tool_result(result_id: str) -> dict[str, Any]:
    """Fetch the full body of a stored tool_result.

    Used by JarvisX's inline expand-card on `[tool_result:...]` refs in
    chat. Returns the raw stored payload so the UI can detect kind
    (edit_file → diff, bash → terminal, read_file → syntax-highlighted)
    and render accordingly.
    """
    from core.runtime.config import TOOL_RESULTS_DIR
    safe_id = result_id.strip()
    if not safe_id.replace("-", "").replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="invalid result_id")
    p = (TOOL_RESULTS_DIR / f"{safe_id}.json").resolve()
    try:
        p.relative_to(Path(TOOL_RESULTS_DIR).resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="path escape")
    if not p.is_file():
        raise HTTPException(status_code=404, detail="result not found")
    import json as _json
    try:
        data = _json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"parse failed: {exc}")
    return data


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


# ── Process supervisor surface ────────────────────────────────────
# Backs the JarvisX bottom-drawer terminal panel: list managed
# background processes Jarvis has spawned, tail their logs, stop them.
# Only `owner` can stop/remove — members observe.


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


@router.get("/processes")
def list_managed_processes(include_stopped: bool = Query(default=True)) -> dict[str, Any]:
    """List processes Jarvis has spawned via the process_supervisor."""
    from core.services.process_supervisor import list_processes
    return list_processes(include_stopped=include_stopped)


@router.get("/processes/{name}/log")
def tail_managed_process_log(
    name: str,
    lines: int = Query(default=200, ge=1, le=2000),
) -> dict[str, Any]:
    """Return the tail of a managed process's combined stdout/stderr log.

    Used by the JarvisX terminal drawer for polling-based live tail.
    """
    from core.services.process_supervisor import tail_process_log
    out = tail_process_log(name, lines=lines)
    if out.get("status") == "error":
        raise HTTPException(status_code=404, detail=out.get("error") or "log unavailable")
    return out


@router.post("/processes/{name}/stop")
def stop_managed_process(name: str, grace: int = Query(default=5, ge=0, le=60)) -> dict[str, Any]:
    """SIGTERM (then SIGKILL after grace) a managed process. Owner-only."""
    _require_owner()
    from core.services.process_supervisor import stop_process
    out = stop_process(name, grace=grace)
    if out.get("status") == "error":
        raise HTTPException(status_code=400, detail=out.get("error") or "stop failed")
    return out


@router.delete("/processes/{name}")
def remove_managed_process(name: str) -> dict[str, Any]:
    """Remove a stopped process from the registry. Owner-only.

    Refuses if the process is still alive — caller must stop first.
    """
    _require_owner()
    from core.services.process_supervisor import remove_process
    out = remove_process(name)
    if out.get("status") == "error":
        raise HTTPException(status_code=400, detail=out.get("error") or "remove failed")
    return out


# ── Claude Code dispatch dashboard ────────────────────────────────
# Backs the JarvisX "Dispatches" view: see Jarvis' parallel
# Claude-Code instances live — what they're working on, how far
# they've gotten (live worktree diff), tokens burned, time elapsed.
# Read-only: dispatching itself happens through the dispatch_to_claude_code
# tool. This is observability, not control.


@router.get("/dispatches")
def list_dispatches(limit: int = Query(default=50, ge=1, le=200)) -> dict[str, Any]:
    """Recent dispatches, running first then by started_at desc.

    Each row carries a parsed copy of the spec for at-a-glance prompt
    preview + elapsed seconds for live ticker rendering.
    """
    import json as _json
    from core.runtime.db import connect

    with connect() as conn:
        rows = conn.execute(
            """
            SELECT task_id, started_at, ended_at, status, tokens_used,
                   exit_code, diff_summary, error, spec_json
            FROM claude_dispatch_audit
            ORDER BY
                CASE WHEN status = 'running' THEN 0 ELSE 1 END,
                started_at DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()

    out: list[dict[str, Any]] = []
    now = datetime.utcnow()
    for r in rows:
        spec: dict[str, Any] = {}
        try:
            spec = _json.loads(r["spec_json"]) if r["spec_json"] else {}
        except Exception:
            spec = {}
        # Compute elapsed for running tasks (live ticker)
        elapsed: float | None = None
        try:
            t0 = datetime.fromisoformat(str(r["started_at"]).replace("Z", "+00:00"))
            t1_raw = r["ended_at"]
            t1 = (
                datetime.fromisoformat(str(t1_raw).replace("Z", "+00:00"))
                if t1_raw
                else now.replace(tzinfo=t0.tzinfo)
            )
            elapsed = max(0.0, (t1 - t0).total_seconds())
        except Exception:
            elapsed = None
        out.append({
            "task_id": r["task_id"],
            "status": r["status"],
            "started_at": r["started_at"],
            "ended_at": r["ended_at"],
            "elapsed_seconds": elapsed,
            "tokens_used": int(r["tokens_used"] or 0),
            "exit_code": r["exit_code"],
            "diff_summary": r["diff_summary"],
            "error": r["error"],
            "prompt": (spec.get("prompt") or "")[:500],  # preview only
            "branch": f"claude/{r['task_id']}",
            "model": spec.get("model"),
            "max_turns": spec.get("max_turns"),
            "allowed_paths": spec.get("allowed_paths") or [],
        })
    return {"count": len(out), "dispatches": out}


@router.get("/dispatches/budget")
def dispatch_budget() -> dict[str, Any]:
    """Current hour's dispatch budget — count + tokens vs caps."""
    from core.runtime.db import connect
    from core.tools.claude_dispatch.budget import (
        MAX_DISPATCHES_PER_HOUR,
        MAX_TOKENS_PER_HOUR,
    )

    bucket = datetime.utcnow().strftime("%Y-%m-%dT%H")
    with connect() as conn:
        row = conn.execute(
            "SELECT dispatch_count, tokens_used FROM claude_dispatch_budget WHERE hour_bucket=?",
            (bucket,),
        ).fetchone()
    count = int(row["dispatch_count"]) if row else 0
    tokens = int(row["tokens_used"]) if row else 0
    return {
        "hour_bucket": bucket,
        "dispatches_used": count,
        "dispatches_max": MAX_DISPATCHES_PER_HOUR,
        "tokens_used": tokens,
        "tokens_max": MAX_TOKENS_PER_HOUR,
    }


@router.get("/dispatches/{task_id}")
def get_dispatch(task_id: str) -> dict[str, Any]:
    """Full audit row + parsed spec for a single dispatch."""
    import json as _json
    from core.tools.claude_dispatch.audit import read_audit_row

    row = read_audit_row(task_id)
    if not row:
        raise HTTPException(status_code=404, detail="dispatch not found")
    spec: dict[str, Any] = {}
    try:
        spec = _json.loads(row.get("spec_json") or "{}")
    except Exception:
        spec = {}
    return {**row, "spec": spec}


@router.get("/dispatches/{task_id}/diff")
def get_dispatch_diff(task_id: str) -> dict[str, Any]:
    """Live diff of a dispatch's worktree against main.

    For running tasks: subprocess git-diff on the worktree on every
    request (cheap, no caching — we want freshness during a live run).
    For finished tasks: returns the persisted diff_summary if any,
    plus the final stored worktree diff if the worktree still exists.
    Worktrees are cleaned up after dispatch finishes, so finished
    tasks may only have the diff_summary string.
    """
    from core.tools.claude_dispatch.audit import read_audit_row
    from core.tools.claude_dispatch.jail import build_worktree_path
    try:
        from core.tools.claude_dispatch.worktree import worktree_diff
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"worktree module unavailable: {exc}")

    row = read_audit_row(task_id)
    if not row:
        raise HTTPException(status_code=404, detail="dispatch not found")

    # Always try a live diff first — gives us real-time visibility
    # while the task is mid-run, and a final snapshot just after it
    # finishes (before cleanup).
    diff_text = ""
    worktree_alive = False
    try:
        wt_path = build_worktree_path(task_id)
        worktree_alive = wt_path.is_dir()
    except Exception:
        worktree_alive = False
    if worktree_alive:
        try:
            diff_text = worktree_diff(task_id)
        except Exception as exc:
            diff_text = f"(diff unavailable: {exc})"
    return {
        "task_id": task_id,
        "status": row.get("status"),
        "worktree_alive": worktree_alive,
        "diff": diff_text,
        "diff_summary": row.get("diff_summary"),
    }


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


# ── Authentication: bearer-token issuance + verification ──────────
# The middleware verifies tokens on every request; these endpoints let
# the owner mint new tokens (e.g. for Mikkel's device) and let clients
# self-check that a stored token is still valid.


class _IssueTokenPayload(BaseModel):
    user_id: str
    role: str = "member"
    ttl_days: int = 30


@router.post("/auth/issue")
def issue_auth_token(payload: _IssueTokenPayload) -> dict[str, Any]:
    """Mint a signed bearer token for a user. Owner-only.

    Returns the token + metadata. The owner is expected to deliver the
    token to the recipient out-of-band (Discord DM, paper, etc.) — we
    don't transport it through any third-party channel.
    """
    _require_owner()
    from core.runtime.jarvisx_auth import issue_token
    try:
        out = issue_token(
            user_id=payload.user_id,
            role=payload.role,
            ttl_days=payload.ttl_days,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return out


from fastapi import Header  # noqa: E402


@router.get("/auth/whoami-token")
def whoami_token(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    """Inspect the bearer token attached to this request.

    Public endpoint (in the middleware's auth-bypass list) so clients
    can verify a stored token without already being authenticated.
    Returns the claims if valid, or the error reason if not.
    """
    if not authorization:
        return {"valid": False, "error": "no Authorization header"}
    try:
        from core.runtime.jarvisx_auth import verify_token
        claims = verify_token(authorization)
    except Exception as exc:
        return {"valid": False, "error": str(exc)}
    return {
        "valid": True,
        "user_id": claims.get("sub"),
        "role": claims.get("role"),
        "issued_at": claims.get("iat"),
        "expires_at": claims.get("exp"),
        "issuer": claims.get("iss"),
    }


# ── Plan proposals (interactive plan-mode) ────────────────────────
# When Jarvis enters plan-mode he writes a structured proposal via the
# propose_plan tool instead of executing. These endpoints let JarvisX
# surface those proposals as interactive cards (approve/dismiss buttons)
# rather than the user having to type the approval into chat.


@router.get("/plans")
def list_plans(
    session_id: str = Query(..., description="Chat session id"),
    include_resolved: bool = Query(default=False),
) -> dict[str, Any]:
    """Pending plan proposals for a session (optionally including resolved)."""
    from core.services.plan_proposals import list_session_plans
    plans = list_session_plans(session_id)
    if not include_resolved:
        plans = [p for p in plans if p.get("status") == "awaiting_approval"]
    return {"session_id": session_id, "count": len(plans), "plans": plans}


@router.post("/plans/{plan_id}/approve")
def approve_plan(plan_id: str) -> dict[str, Any]:
    """Mark a plan as approved. Owner-only."""
    _require_owner()
    from core.services.plan_proposals import resolve_plan
    out = resolve_plan(plan_id, decision="approved")
    if out.get("status") == "error":
        raise HTTPException(status_code=404, detail=out.get("error") or "plan not found")
    return out


@router.post("/plans/{plan_id}/dismiss")
def dismiss_plan(plan_id: str) -> dict[str, Any]:
    """Mark a plan as dismissed. Owner-only."""
    _require_owner()
    from core.services.plan_proposals import resolve_plan
    out = resolve_plan(plan_id, decision="dismissed")
    if out.get("status") == "error":
        raise HTTPException(status_code=404, detail=out.get("error") or "plan not found")
    return out


# ── Session forking ───────────────────────────────────────────────
# "Fork from here" = create a new session with a copy of all messages
# up to and including a given message_id. Useful for exploring a
# different direction without losing the original conversation.


class _ForkPayload(BaseModel):
    source_session_id: str
    up_to_message_id: str
    title: str | None = None


@router.post("/sessions/fork")
def fork_session(payload: _ForkPayload) -> dict[str, Any]:
    """Clone a session up to a specific message_id.

    Copies user/assistant/tool/compact_marker messages in order until
    we've copied the target message_id (inclusive), then stops. The new
    session has its own id; the original is untouched.
    """
    from core.services.chat_sessions import (
        get_chat_session,
        create_chat_session,
        append_chat_message,
    )
    src = get_chat_session(payload.source_session_id)
    if src is None:
        raise HTTPException(status_code=404, detail="source session not found")
    messages = src.get("messages") or []
    if not isinstance(messages, list):
        raise HTTPException(status_code=500, detail="malformed source session")

    # Default title: source title + " (forked)"
    src_title = str(src.get("title") or "Forked chat")
    new_title = (payload.title or f"{src_title} (forked)").strip()[:200] or "Forked chat"
    new_session = create_chat_session(title=new_title)
    new_id = str(new_session.get("id") or "")
    if not new_id:
        raise HTTPException(status_code=500, detail="failed to create session")

    copied = 0
    found_target = False
    for m in messages:
        if not isinstance(m, dict):
            continue
        role = str(m.get("role") or "").strip()
        # Only copy roles append_chat_message accepts; skip approval_request
        # and other UI-side virtual roles.
        if role not in {"user", "assistant", "tool", "compact_marker"}:
            continue
        content = str(m.get("content") or "").strip()
        if not content:
            continue
        try:
            append_chat_message(
                session_id=new_id,
                role=role,
                content=content,
                created_at=str(m.get("created_at") or m.get("ts") or "") or None,
            )
            copied += 1
        except Exception as exc:
            logger.warning("fork: skip message: %s", exc)
        if str(m.get("message_id") or m.get("id") or "") == payload.up_to_message_id:
            found_target = True
            break

    if not found_target:
        # Couldn't find the target message — clean up empty session?
        # Leave it; the user got *some* fork and can decide.
        logger.info(
            "fork: target message %s not found; copied %d messages",
            payload.up_to_message_id, copied,
        )

    return {
        "status": "ok",
        "new_session_id": new_id,
        "title": new_title,
        "messages_copied": copied,
        "found_target": found_target,
    }


# ── Process spawn (owner-only) ────────────────────────────────────
# Lets the JarvisX TaskBar trigger predefined commands via the
# process_supervisor. Read/list/stop already public above.


class _SpawnPayload(BaseModel):
    name: str
    command: str
    cwd: str | None = None
    replace_if_running: bool = True


@router.post("/processes")
def spawn_managed_process(payload: _SpawnPayload) -> dict[str, Any]:
    """Spawn a managed background process. Owner-only.

    Wraps process_supervisor.spawn_process. Caller-supplied cwd is
    used verbatim; the supervisor itself handles env, log routing,
    and the reaper thread.
    """
    _require_owner()
    from core.services.process_supervisor import spawn_process
    out = spawn_process(
        name=payload.name,
        command=payload.command,
        cwd=payload.cwd,
        replace_if_running=payload.replace_if_running,
    )
    if out.get("status") == "error":
        raise HTTPException(status_code=400, detail=out.get("error") or "spawn failed")
    return out


# ── Trading dashboard (read-only) ─────────────────────────────────
# Read-only window into the grid bot's state. Jarvis writes the
# state file from his trading code at his own pace; this endpoint
# just exposes whatever's there to the JarvisX TradingView.
#
# Contract: ~/.jarvis-v2/state/trading_state.json
#
#   {
#     "status": "inactive" | "active" | "paused" | "stopped" | "error",
#     "mode": "paper" | "simulation" | "testnet" | "live",
#     "symbol": "BTCUSDT",
#     "config": {
#       "grid_levels": int, "grid_spacing_pct": float,
#       "order_size_usdt": float, "stop_loss_pct": float
#     },
#     "capital": {
#       "usdt": float, "asset": float, "asset_symbol": "BTC",
#       "total_value_usdt": float, "starting_value_usdt": float
#     },
#     "pnl": {
#       "realized_today": float, "realized_total": float,
#       "unrealized": float, "fees_today": float, "fees_total": float
#     },
#     "drawdown": {
#       "current_pct": float, "max_pct_today": float, "cap_pct": float
#     },
#     "trades_today": int,
#     "open_orders": [{"id", "side", "price", "quantity", "placed_at"}],
#     "recent_trades": [{"type", "price", "qty", "profit_usdt?", "timestamp"}],
#     "last_price": float,
#     "last_updated": ISO timestamp,
#     "last_error": str?  # set when status == 'error'
#   }
#
# When the file doesn't exist or is unparsable, we return a synthetic
# "inactive" record so the UI has something to render. No 500s.


@router.get("/trading/state")
def trading_state() -> dict[str, Any]:
    """Read the current trading-bot state. Read-only.

    Public read (no _require_owner) on the assumption that the running
    bot's PnL is part of what JarvisX members may want to see — same
    privacy posture as MoodPill / PresencePill. If you want this gated,
    flip the call site.
    """
    import json as _json
    from core.runtime.config import STATE_DIR
    state_file = Path(STATE_DIR) / "trading_state.json"
    if not state_file.is_file():
        return _trading_inactive_default("no state file written yet")
    try:
        raw = state_file.read_text(encoding="utf-8")
        data = _json.loads(raw)
    except _json.JSONDecodeError as exc:
        return _trading_inactive_default(f"state file malformed: {exc}")
    except Exception as exc:
        return _trading_inactive_default(f"state read failed: {exc}")
    if not isinstance(data, dict):
        return _trading_inactive_default("state file is not a dict")
    # Don't validate the full schema — the bot's contract may evolve.
    # The UI tolerates missing fields. Just stamp last_seen for the UI
    # so it can show "data is N seconds old".
    try:
        mtime = state_file.stat().st_mtime
        data["_state_file_mtime"] = mtime
    except Exception:
        pass
    return data


def _trading_inactive_default(reason: str) -> dict[str, Any]:
    """Synthetic 'inactive' state so UI always has something to render."""
    return {
        "status": "inactive",
        "mode": "paper",
        "symbol": "",
        "config": {},
        "capital": {
            "usdt": 0.0, "asset": 0.0, "asset_symbol": "",
            "total_value_usdt": 0.0, "starting_value_usdt": 0.0,
        },
        "pnl": {
            "realized_today": 0.0, "realized_total": 0.0,
            "unrealized": 0.0, "fees_today": 0.0, "fees_total": 0.0,
        },
        "drawdown": {"current_pct": 0.0, "max_pct_today": 0.0, "cap_pct": 5.0},
        "trades_today": 0,
        "open_orders": [],
        "recent_trades": [],
        "last_price": 0.0,
        "last_updated": None,
        "_inactive_reason": reason,
    }
