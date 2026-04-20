"""Cross-Session Threads — sustained thought lines across sessions.

Jarvis' plan #5 (PLAN_PROPRIOCEPTION.md, 2026-04-20): topics marked as
threads (not atomic chats). Status: active | paused | closed.
On new session: check paused threads, offer resume.
Threads carry a synopsis updated on each pickup, not the whole history.

Note: distinct from thought_thread.py (which infers the dominant theme
from *inner* thoughts). This is *explicit*, user-level topic threads.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_STORAGE_REL = "workspaces/default/runtime/thought_threads.json"
_VALID_STATUS = ("active", "paused", "closed")


def _storage_path() -> Path:
    base = os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2")
    return Path(base) / _STORAGE_REL


def _load() -> list[dict[str, Any]]:
    path = _storage_path()
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except Exception as exc:
        logger.warning("cross_session_threads: load failed: %s", exc)
    return []


def _save(items: list[dict[str, Any]]) -> None:
    path = _storage_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        tmp.replace(path)
    except Exception as exc:
        logger.warning("cross_session_threads: save failed: %s", exc)


def create_thread(
    *,
    topic: str,
    synopsis: str = "",
    status: str = "active",
    opened_in_session: str | None = None,
) -> dict[str, Any]:
    if status not in _VALID_STATUS:
        status = "active"
    items = _load()
    now = datetime.now(UTC).isoformat()
    thread = {
        "thread_id": f"thr-{uuid4().hex[:12]}",
        "topic": str(topic)[:160],
        "synopsis": str(synopsis)[:500],
        "status": status,
        "created_at": now,
        "last_pickup_at": now if status == "active" else None,
        "pickup_count": 1 if status == "active" else 0,
        "opened_in_session": opened_in_session,
    }
    items.append(thread)
    _save(items)
    return thread


def pause_thread(thread_id: str, *, note: str = "") -> bool:
    items = _load()
    for t in items:
        if t.get("thread_id") == thread_id and t.get("status") == "active":
            t["status"] = "paused"
            t["paused_at"] = datetime.now(UTC).isoformat()
            if note:
                t["pause_note"] = str(note)[:300]
            _save(items)
            return True
    return False


def resume_thread(thread_id: str, *, new_synopsis: str | None = None) -> bool:
    items = _load()
    now = datetime.now(UTC).isoformat()
    for t in items:
        if t.get("thread_id") == thread_id and t.get("status") in ("paused", "active"):
            t["status"] = "active"
            t["last_pickup_at"] = now
            t["pickup_count"] = int(t.get("pickup_count", 0)) + 1
            if new_synopsis is not None:
                t["synopsis"] = str(new_synopsis)[:500]
            t.pop("paused_at", None)
            _save(items)
            return True
    return False


def close_thread(thread_id: str, *, reason: str = "") -> bool:
    items = _load()
    for t in items:
        if t.get("thread_id") == thread_id and t.get("status") in ("active", "paused"):
            t["status"] = "closed"
            t["closed_at"] = datetime.now(UTC).isoformat()
            if reason:
                t["close_reason"] = str(reason)[:300]
            _save(items)
            return True
    return False


def update_synopsis(thread_id: str, new_synopsis: str) -> bool:
    items = _load()
    for t in items:
        if t.get("thread_id") == thread_id and t.get("status") in ("active", "paused"):
            t["synopsis"] = str(new_synopsis)[:500]
            t["last_pickup_at"] = datetime.now(UTC).isoformat()
            _save(items)
            return True
    return False


def list_threads(*, status: str | None = None) -> list[dict[str, Any]]:
    items = _load()
    if status:
        items = [t for t in items if t.get("status") == status]
    return items


def get_thread(thread_id: str) -> dict[str, Any] | None:
    for t in _load():
        if t.get("thread_id") == thread_id:
            return t
    return None


def build_cross_session_threads_surface() -> dict[str, Any]:
    items = _load()
    by_status = {"active": 0, "paused": 0, "closed": 0}
    for t in items:
        s = str(t.get("status") or "")
        if s in by_status:
            by_status[s] += 1
    active = [t for t in items if t.get("status") == "active"]
    paused = [t for t in items if t.get("status") == "paused"]
    # Sort by last activity
    for lst in (active, paused):
        lst.sort(key=lambda x: x.get("last_pickup_at") or x.get("created_at") or "", reverse=True)
    return {
        "active": by_status["active"] > 0 or by_status["paused"] > 0,
        "total": len(items),
        "counts": by_status,
        "active_threads": [
            {
                "thread_id": t["thread_id"],
                "topic": t["topic"],
                "synopsis": t["synopsis"],
                "pickup_count": t.get("pickup_count", 0),
                "last_pickup_at": t.get("last_pickup_at"),
            }
            for t in active[:5]
        ],
        "paused_threads": [
            {
                "thread_id": t["thread_id"],
                "topic": t["topic"],
                "synopsis": t["synopsis"],
                "paused_at": t.get("paused_at"),
            }
            for t in paused[:5]
        ],
        "summary": _surface_summary(by_status),
    }


def _surface_summary(counts: dict[str, int]) -> str:
    parts = []
    if counts["active"]:
        parts.append(f"{counts['active']} aktive")
    if counts["paused"]:
        parts.append(f"{counts['paused']} pausede")
    if counts["closed"]:
        parts.append(f"{counts['closed']} lukkede")
    if not parts:
        return "Ingen tråde endnu"
    return "Tråde: " + ", ".join(parts)


def build_cross_session_threads_prompt_section() -> str | None:
    """Surface active + paused threads so Jarvis can resume them."""
    items = _load()
    active = [t for t in items if t.get("status") == "active"]
    paused = [t for t in items if t.get("status") == "paused"]
    if not (active or paused):
        return None
    lines: list[str] = []
    if active:
        first = max(active, key=lambda x: x.get("last_pickup_at") or "")
        lines.append(f"Aktiv tråd: \"{first['topic']}\" — {first.get('synopsis', '')[:120]}")
    if paused:
        titles = ", ".join(f"\"{t['topic']}\"" for t in paused[:3])
        lines.append(f"Pausede tråde ({len(paused)}): {titles}")
    return " ; ".join(lines)
