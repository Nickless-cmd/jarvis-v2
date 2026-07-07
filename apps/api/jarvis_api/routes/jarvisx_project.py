"""JarvisX project-anchor + file-watch route group.

Project tree/list/read, per-project notes persistence, and an
mtime-polling file watcher. Extracted from routes/jarvisx.py.

Behavior-preserving: pure code movement, no logic changes.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from apps.api.jarvis_api.routes.jarvisx_common import logger

router = APIRouter(prefix="/api", tags=["jarvisx"])


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
