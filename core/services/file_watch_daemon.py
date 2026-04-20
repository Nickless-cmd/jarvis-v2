"""File Watch Daemon — proprioception: "I feel when my own files change".

Jarvis' plan #1 (PLAN_PROPRIOCEPTION.md, 2026-04-20): monitor workspace
and repo-root files so Jarvis perceives modifications to his own body as
events on the bus.

Implementation note: the plan proposed `watchdog` + inotify. That library
is not installed in the ai env, so this daemon uses **mtime polling** on
heartbeat tick — cheap, dependency-free, good enough at tick cadence.

Scope: ~/.jarvis-v2/workspaces/default/ and code repo root (CLAUDE.md,
core/services/*.py). Ignore patterns: .pyc, __pycache__, .tmp, .git.

Emits `file_watch.change` events with {path, change_type, when, diff_preview}.
Keeps a rolling log of recent changes for MC surface.
"""
from __future__ import annotations

import logging
import os
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Deque

logger = logging.getLogger(__name__)

_WATCHED_EXTENSIONS: frozenset[str] = frozenset({".md", ".py", ".json", ".yaml", ".toml"})
_IGNORE_FRAGMENTS: tuple[str, ...] = (
    "__pycache__", ".git/", ".tmp", ".pyc", "node_modules", ".venv",
    "/runtime/", "scheduled_windows.json", "jobs_queue.json",
    "memory_review_queue.json", "outcome_learning.json", "prompt_mutations.json",
    "automations.json", "spaced_repetition.json", "day_shapes.json",
    "creative_projects.json", "file_watch_state.json", "somatic_history.json",
    "reboot_markers.json", "thought_threads.json",
)

_RECENT_MAX = 50
_recent: Deque[dict[str, Any]] = deque(maxlen=_RECENT_MAX)

# mtime fingerprint: {path: (mtime, size)}
_fingerprint: dict[str, tuple[float, int]] = {}
_first_scan_done: bool = False


def _should_ignore(path_str: str) -> bool:
    return any(frag in path_str for frag in _IGNORE_FRAGMENTS)


def _watched_roots() -> list[Path]:
    roots: list[Path] = []
    # Workspace
    base = os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2")
    ws = Path(base) / "workspaces/default"
    if ws.exists():
        roots.append(ws)
    # Repo root (CLAUDE.md / core/services)
    repo = Path(__file__).resolve().parents[2]
    if (repo / "CLAUDE.md").exists():
        roots.append(repo / "CLAUDE.md")
    services = repo / "core/services"
    if services.exists():
        roots.append(services)
    return roots


def _iter_watched_files(root: Path):
    if root.is_file():
        if root.suffix in _WATCHED_EXTENSIONS and not _should_ignore(str(root)):
            yield root
        return
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix not in _WATCHED_EXTENSIONS:
            continue
        if _should_ignore(str(p)):
            continue
        yield p


def _diff_preview(path: Path) -> str:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            lines = [next(f, "") for _ in range(5)]
        return "".join(lines).strip()[:240]
    except Exception:
        return ""


def _record_change(path: Path, change_type: str) -> None:
    entry = {
        "path": str(path),
        "rel_path": _compact_path(path),
        "change_type": change_type,
        "when": datetime.now(UTC).isoformat(),
        "diff_preview": _diff_preview(path) if change_type != "deleted" else "",
    }
    _recent.appendleft(entry)
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish({
            "kind": "file_watch.change",
            "payload": entry,
        })
    except Exception:
        pass


def _compact_path(path: Path) -> str:
    s = str(path)
    home = os.path.expanduser("~")
    if s.startswith(home):
        s = "~" + s[len(home):]
    # Also compact repo path
    try:
        repo = Path(__file__).resolve().parents[2]
        repo_str = str(repo)
        if s.startswith(repo_str):
            s = "<repo>" + s[len(repo_str):]
    except Exception:
        pass
    return s


def tick(_seconds: float = 0.0) -> dict[str, Any]:
    """One polling sweep across watched roots."""
    global _first_scan_done
    seen_paths: set[str] = set()
    changes = 0
    try:
        for root in _watched_roots():
            for path in _iter_watched_files(root):
                path_str = str(path)
                seen_paths.add(path_str)
                try:
                    st = path.stat()
                except Exception:
                    continue
                current = (st.st_mtime, st.st_size)
                prev = _fingerprint.get(path_str)
                if prev is None:
                    _fingerprint[path_str] = current
                    if _first_scan_done:
                        _record_change(path, "created")
                        changes += 1
                elif prev != current:
                    _fingerprint[path_str] = current
                    _record_change(path, "modified")
                    changes += 1
        # Detect deletions
        if _first_scan_done:
            missing = set(_fingerprint.keys()) - seen_paths
            for path_str in missing:
                try:
                    _record_change(Path(path_str), "deleted")
                except Exception:
                    pass
                del _fingerprint[path_str]
                changes += 1
        _first_scan_done = True
    except Exception as exc:
        logger.debug("file_watch_daemon.tick failed: %s", exc)
    return {"changes": changes, "tracked": len(_fingerprint)}


def recent_changes(*, limit: int = 20) -> list[dict[str, Any]]:
    return list(_recent)[:limit]


def build_file_watch_surface() -> dict[str, Any]:
    recent = recent_changes(limit=10)
    by_type: dict[str, int] = {}
    for r in recent:
        t = str(r.get("change_type") or "")
        by_type[t] = by_type.get(t, 0) + 1
    return {
        "active": _first_scan_done,
        "tracked_files": len(_fingerprint),
        "recent_changes": recent,
        "changes_by_type_recent": by_type,
        "summary": _surface_summary(recent),
    }


def _surface_summary(recent: list[dict[str, Any]]) -> str:
    if not recent:
        return f"Overvåger {len(_fingerprint)} filer — ingen ændringer endnu"
    newest = recent[0]
    when = str(newest.get("when") or "")[:19]
    return (
        f"{len(recent)} ændring(er) seneste: "
        f"{newest.get('change_type')} {newest.get('rel_path')} @ {when}"
    )


def build_file_watch_prompt_section() -> str | None:
    """Surface recent changes briefly — stays quiet if nothing recent."""
    recent = recent_changes(limit=5)
    if not recent:
        return None
    # Only surface if changes are very recent (last 10 min)
    now = datetime.now(UTC)
    from datetime import timedelta
    fresh = []
    for r in recent:
        try:
            when = datetime.fromisoformat(str(r.get("when")).replace("Z", "+00:00"))
            if (now - when) <= timedelta(minutes=10):
                fresh.append(r)
        except Exception:
            continue
    if not fresh:
        return None
    lines = [
        f"{r.get('change_type')}: {r.get('rel_path')}"
        for r in fresh[:3]
    ]
    return "Mine filer ændrede sig lige: " + "; ".join(lines)


def reset_file_watch() -> None:
    """Reset state (for testing)."""
    global _first_scan_done
    _fingerprint.clear()
    _recent.clear()
    _first_scan_done = False
